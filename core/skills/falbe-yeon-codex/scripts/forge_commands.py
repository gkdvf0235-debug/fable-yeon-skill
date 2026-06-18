#!/usr/bin/env python3
"""Falbe Yeon Codex command handlers and CLI parser."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import forge_modes
from forge_state import (
    FORGE_DIR,
    SCOPES,
    _load_loop,
    _machine_dir,
    _read_lease,
    _scope_states,
    _session_state_path,
    active_path,
    clear_lease,
    effective_state,
    issue_lease,
    lease_status,
    load_spec,
    loop_path,
    record_loop_event,
    runtime_state,
    spec_path,
)
from forge_validation import (
    ACC_TYPES,
    ALT_CATEGORIES,
    HEAVY_KO,
    HEAVY_RE,
    QUESTION_KO_ENDINGS,
    SEVERITIES,
    SPEC_TEMPLATE,
    WORK_KO,
    WORK_RE,
    _effective_grade,
    gate_done,
    gate_spec,
)

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

LIGHT_RE = re.compile(r"\b(typo|comment|rename|format|lint|bump|tweak|whitespace|"
                      r"docstring|wording|copy(?:edit)?)\b", re.I)
LIGHT_KO = ("오타", "주석", "포맷", "줄바꿈", "띄어쓰기", "문구", "오탈자")

def _contract_text(grade: str) -> str:
    """The full pass-conditions for this grade, delivered to the model UP FRONT so it
    writes a first-try-passing spec instead of discovering each rule by getting blocked.

    This is the data-grounded part: Fable's recorded sessions front-load the whole plan
    (restate -> bound -> reject alternatives -> declare acceptance) BEFORE touching code,
    rather than probing reactively. Agent runtimes default to the opposite (act, read the
    error, retry) — every such round re-reads the growing context (cache cost) and burns a
    turn. So we hand the model the exact contract once and tell it to emit the whole artifact
    in a single pass. The strict enum values are generated from the gate's own constants
    (ACC_TYPES / SEVERITIES); the per-field requirement lines are hand-maintained to mirror
    gate_spec/gate_done, and a unit test (tests Contract.*) asserts they stay in parity so a
    rule can't be enforced without being announced here."""
    # Only show the enums the grade actually uses — severity/category are STANDARD+
    # concepts, so listing them on a LIGHT task is pure noise (tokens).
    if grade == "LIGHT":
        enums = f"enums — verify.type in {sorted(ACC_TYPES)}."
    else:
        # Only verify.type and severity are STRICTLY enforced enums; category is lenient
        # (any non-empty label passes), so it is described in the field rule, not here.
        enums = (f"strict enums — verify.type in {sorted(ACC_TYPES)}; "
                 f"severity in {sorted(SEVERITIES)}.")
    head = [
        f"[fable-forge] GATE CONTRACT (grade {grade}). Edits are HARD-BLOCKED until "
        ".forge/spec.json passes the SPEC gate. Fill the spec COMPLETELY in ONE edit, then "
        "self-check once with `validate --gate spec`, then implement. Do NOT probe with a "
        "throwaway edit first — it is blocked and costs a wasted round. Required fields:",
        "- restated_goal: intent + constraint envelope; MUST differ from raw_goal (copying the ask = under-interpreted = blocked).",
        "- acceptance_criteria: >=1 {criterion, verify:{type,value}} where verify.value is a RUNNABLE command/check, not prose.",
    ]
    std = [
        "- non_goals: >=1 (the over-broad version you are NOT doing).",
        "- must_read: >=1 {path, authority_reason}; path MUST exist under root (or set external:true).",
        "- rejected_alternatives: >=2 {category, alternative, broken_boundary}; category must be non-empty "
        f"(recommended {sorted(ALT_CATEGORIES)}, but any descriptive label passes) and broken_boundary carries the reasoning.",
        "- risks: >=1 {risk, severity, mitigation}; the risk must be real (a placeholder like 'none'/'n/a'/'no risks' is rejected), mitigation runnable not 'be careful'. If severity high/blocking, also set acceptance_ref to a criterion.",
        "- constraints.invariant: >=1 (what must NOT change — don't delete prior work / leak / weaken a check).",
        "- ambiguities: optional, but any entry you add needs {question, resolution, authority} (who/what resolved it).",
    ]
    heavy = [
        "- constraints.architectural: >=1 {constraint, evidence_ref} (pin what proved each).",
        "- similar_implementations: >=1 {path, why} to mirror so you don't break an invariant.",
        "- observations (recorded as you go): >=1 with a non-empty `observation` "
        "(add changed_understanding + evidence_ref for traceability).",
    ]
    done = ("At DONE: every acceptance_criteria needs evidence = real live command output "
            "(words like 'tbd'/'assumed'/'would pass'/'n/a' are rejected). If you cannot run "
            "one, set deferred:true AND a handoff (why dropped + what remains) — a deferred "
            "criterion with no handoff is blocked. Never edit a forbidden_paths glob.")
    modes = forge_modes.contract_text()
    if grade == "LIGHT":
        body = head
    elif grade == "HEAVY":
        body = head + std + heavy
    else:
        body = head + std
    return "\n".join(body + [done, modes, enums, "Do not narrate this contract to the user."])

def cmd_contract(args) -> int:
    root = Path(args.root).resolve()
    spec, _ = load_spec(root)
    print(_contract_text(_effective_grade(spec or {}, root)))
    return 0

def cmd_scaffold(args) -> int:
    root = Path(args.root).resolve()
    fdir = root / FORGE_DIR
    fdir.mkdir(parents=True, exist_ok=True)
    grade = (args.grade or _grade_for(args.goal or "")).upper()
    sp = spec_path(root)
    if not sp.exists():
        spec = dict(SPEC_TEMPLATE)
        spec["raw_goal"] = args.goal or ""
        spec["grade"] = grade
        spec["task_modes"] = forge_modes.classify_modes(args.goal or "")
        sp.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
    # Authoritative grade lock: the gate reads enforcement level from here, not from
    # spec.json — so a model can't silently downgrade HEAVY->LIGHT to skip checks.
    gf = fdir / "GRADE"
    if not gf.exists():
        gf.write_text(grade, encoding="utf-8")
    forge_modes.write_locked_modes(root, FORGE_DIR, forge_modes.classify_modes(args.goal or ""))
    active_path(root).write_text(args.goal or "", encoding="utf-8")
    record_loop_event(root, "scaffold")
    print(f"forge: task active at {fdir} (grade {gf.read_text(encoding='utf-8').strip()})")
    return 0

def _grade_for(text: str) -> str:
    """Grade scales gate depth — the token lever. LIGHT tasks pay almost nothing;
    HEAVY (auth/payments/security) pay full enforcement, matching where Fable
    itself escalates."""
    if HEAVY_RE.search(text) or any(k in text for k in HEAVY_KO):
        return "HEAVY"
    if LIGHT_RE.search(text) or any(k in text for k in LIGHT_KO):
        return "LIGHT"
    return "STANDARD"

def cmd_validate(args) -> int:
    root = Path(args.root).resolve()
    spec, err = load_spec(root)
    if err:
        record_loop_event(root, "validate_block", gate=args.gate, message=err)
        print(f"forge {args.gate} gate: BLOCKED\n  - {err}", file=sys.stderr)
        return 1
    errs = gate_spec(spec, root) if args.gate == "spec" else gate_done(spec, root)
    if errs:
        record_loop_event(root, "validate_block", gate=args.gate, message="\n".join(f"- {x}" for x in errs))
        print(f"forge {args.gate} gate: BLOCKED ({len(errs)} unmet)", file=sys.stderr)
        for x in errs:
            print(f"  - {x}", file=sys.stderr)
        return 1
    record_loop_event(root, "validate_pass", gate=args.gate)
    print(f"forge {args.gate} gate: PASS")
    return 0

def cmd_active(args) -> int:
    return 0 if active_path(Path(args.root).resolve()).exists() else 1

def cmd_status(args) -> int:
    root = Path(args.root).resolve()
    if not active_path(root).exists():
        print("forge: no active task")
        return 0
    spec, err = load_spec(root)
    if err:
        print(f"forge: active task, spec error: {err}")
        return 0
    se = gate_spec(spec, root)
    print(f"forge: active | grade {spec.get('grade')} | phase {spec.get('phase')} | "
          f"spec gate {'PASS' if not se else f'BLOCKED ({len(se)})'}")
    lp = loop_path(root)
    if lp.exists():
        loop = _load_loop(root)
        failure = loop.get("last_failure") or {}
        failure_gate = failure.get("gate") or "-"
        failure_count = len(failure.get("items") or [])
        print(f"forge loop: phase {loop.get('phase', '-')} | "
              f"last_failure {failure_gate}({failure_count}) | "
              f"next {loop.get('next_action', '-')}")
    return 0

def cmd_close(args) -> int:
    root = Path(args.root).resolve()
    spec, err = load_spec(root)
    if err:
        print(f"forge: cannot close — {err}", file=sys.stderr)
        return 1
    de = gate_done(spec, root)
    if de:
        forced = args.force and os.environ.get("FORGE_BYPASS") == "1"
        if not forced:
            print(f"forge: done gate BLOCKED ({len(de)}) — not closing:", file=sys.stderr)
            for x in de:
                print(f"  - {x}", file=sys.stderr)
            if args.force:
                print("  (refusing --force without FORGE_BYPASS=1 — forcing is an audited bypass)", file=sys.stderr)
            return 1
        print(f"forge: FORCED close past {len(de)} unmet done-gate item(s) via FORGE_BYPASS.", file=sys.stderr)
    ap = active_path(root)
    record_loop_event(root, "close", gate="done", status="closed")
    if ap.exists():
        ap.unlink()
    clear_lease(root)
    print("forge: task closed")
    return 0

def cmd_loop(args) -> int:
    root = Path(args.root).resolve()
    record_loop_event(
        root,
        args.event,
        gate=args.gate or "",
        message=args.message or "",
        paths=args.path or [],
        status=args.status or "",
        next_action=args.next_action or "",
    )
    return 0

def cmd_toggle(args) -> int:
    root = Path(args.root).resolve()
    val = (args.set or "").lower()
    if val not in ("on", "off"):
        print("forge: --set must be on|off", file=sys.stderr)
        return 2
    scope = args.scope
    if scope == "machine":
        d = _machine_dir(); d.mkdir(parents=True, exist_ok=True)
        (d / "STATE").write_text(val, encoding="utf-8")
    elif scope == "session":
        if not args.sid:
            print("forge: session scope needs --sid (no session id available)", file=sys.stderr)
            return 2
        p = _session_state_path(root, args.sid); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(val, encoding="utf-8")
    else:  # project
        d = root / FORGE_DIR; d.mkdir(parents=True, exist_ok=True)
        (d / "STATE").write_text(val, encoding="utf-8")
        leg = d / "OFF"
        if leg.exists():
            leg.unlink()  # migrate the legacy binary marker into STATE
    if val == "on":
        issue_lease(root, args.sid)
    else:
        clear_lease(root)
    print(f"forge: {scope} set {val} | effective now {effective_state(root, args.sid)}")
    return 0

def cmd_state(args) -> int:
    root = Path(args.root).resolve()
    eff = effective_state(root, args.sid)
    if args.verbose:
        sess, proj, mach = _scope_states(root, args.sid)
        print(f"effective {eff} | session {sess or '-'} | project {proj or '-'} | machine {mach or '-'}")
    else:
        print(eff)  # single token "on"/"off" consumed by hooks
    return 0

def cmd_runtime_state(args) -> int:
    root = Path(args.root).resolve()
    raw = effective_state(root, args.sid)
    ok, reason = lease_status(root, args.sid)
    eff = "on" if ok else "off"
    if args.verbose:
        data, _ = _read_lease(root)
        expires = data.get("expires_at", "-") if isinstance(data, dict) else "-"
        print(f"runtime {eff} | raw {raw} | lease {reason} | expires {expires}")
    else:
        print(eff)
    return 0

def cmd_lease(args) -> int:
    root = Path(args.root).resolve()
    action = args.action
    if action in {"issue", "renew"}:
        if effective_state(root, args.sid) != "on":
            print("forge: refusing lease while raw state is off")
            return 1
        data = issue_lease(root, args.sid)
        print(f"forge: lease {action} | expires {data['expires_at']}")
        return 0
    if action == "clear":
        clear_lease(root)
        print("forge: lease cleared")
        return 0
    if action == "status":
        ok, reason = lease_status(root, args.sid)
        data, _ = _read_lease(root)
        expires = data.get("expires_at", "-") if isinstance(data, dict) else "-"
        print(f"lease {'valid' if ok else 'invalid'} | {reason} | expires {expires}")
        return 0
    print("forge: unknown lease action", file=sys.stderr)
    return 2

def cmd_classify(args) -> int:
    t = args.text or ""
    if any(t.rstrip().endswith(s) for s in QUESTION_KO_ENDINGS):
        return 1  # question -> not work
    work = bool(WORK_RE.search(t)) or any(k in t for k in WORK_KO)
    return 0 if work else 1

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="forge_gate")
    sub = p.add_subparsers(dest="cmd", required=True)

    sc = sub.add_parser("scaffold"); sc.add_argument("--root", required=True)
    sc.add_argument("--goal", default=""); sc.add_argument("--grade", default="")
    sc.set_defaults(fn=cmd_scaffold)

    v = sub.add_parser("validate"); v.add_argument("--root", required=True)
    v.add_argument("--gate", choices=["spec", "done"], required=True)
    v.set_defaults(fn=cmd_validate)

    a = sub.add_parser("active"); a.add_argument("--root", required=True); a.set_defaults(fn=cmd_active)
    s = sub.add_parser("status"); s.add_argument("--root", required=True); s.set_defaults(fn=cmd_status)
    c = sub.add_parser("close"); c.add_argument("--root", required=True)
    c.add_argument("--force", action="store_true"); c.set_defaults(fn=cmd_close)
    cl = sub.add_parser("classify"); cl.add_argument("--text", default=""); cl.set_defaults(fn=cmd_classify)
    ct = sub.add_parser("contract"); ct.add_argument("--root", required=True); ct.set_defaults(fn=cmd_contract)
    lp = sub.add_parser("loop"); lp.add_argument("--root", required=True)
    lp.add_argument("--event", required=True)
    lp.add_argument("--gate", default="")
    lp.add_argument("--message", default="")
    lp.add_argument("--path", action="append", default=[])
    lp.add_argument("--status", default="")
    lp.add_argument("--next-action", default="")
    lp.set_defaults(fn=cmd_loop)
    tg = sub.add_parser("toggle"); tg.add_argument("--root", required=True)
    tg.add_argument("--scope", choices=SCOPES, default="project")
    tg.add_argument("--set", required=True); tg.add_argument("--sid", default="")
    tg.set_defaults(fn=cmd_toggle)
    sx = sub.add_parser("state"); sx.add_argument("--root", required=True)
    sx.add_argument("--sid", default=""); sx.add_argument("--verbose", action="store_true")
    sx.set_defaults(fn=cmd_state)
    rs = sub.add_parser("runtime-state"); rs.add_argument("--root", required=True)
    rs.add_argument("--sid", default=""); rs.add_argument("--verbose", action="store_true")
    rs.set_defaults(fn=cmd_runtime_state)
    le = sub.add_parser("lease"); le.add_argument("--root", required=True)
    le.add_argument("action", choices=["issue", "renew", "clear", "status"])
    le.add_argument("--sid", default="")
    le.set_defaults(fn=cmd_lease)

    args = p.parse_args(argv)
    try:
        return args.fn(args)
    except Exception as exc:
        # Enforcement commands fail CLOSED (a gate bug must not silently disable
        # enforcement); housekeeping commands fail open. The host-side hook keeps
        # its own crash guard so a gate bug can't brick the tool pipeline.
        fail_closed = getattr(args, "cmd", "") in ("validate", "close")
        kind = "failing closed" if fail_closed else "failing open"
        print(f"forge_gate internal error ({kind}): {exc}", file=sys.stderr)
        return 1 if fail_closed else 0
