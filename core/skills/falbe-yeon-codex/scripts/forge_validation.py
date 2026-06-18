#!/usr/bin/env python3
"""Falbe Yeon Codex spec and completion validation."""
from __future__ import annotations

import fnmatch
import re
from pathlib import Path

import forge_modes
from forge_state import FORGE_DIR

ALT_CATEGORIES = {"tempting_shortcut", "architecture", "scope", "compatibility"}
NO_RISK_PLACEHOLDERS = {"none", "n/a", "na", "no risk", "no risks", "nothing", "no"}
SEVERITIES = {"low", "medium", "high", "blocking"}
ACC_TYPES = {"command", "grep", "stat", "artifact", "human_visual", "test"}
FAKE_MARKERS = ("not run", "notrun", "did not run", "didn't run", "assumed",
                "would pass", "should pass", "to be done", "tbd", "todo",
                "n/a", "pending", "placeholder", "will run", "not yet")
SPEC_TEMPLATE = {
    "grade": "STANDARD",
    "phase": "SPEC",
    "raw_goal": "",
    "restated_goal": "",
    "non_goals": [],
    "ambiguities": [],              # {question, resolution, authority}
    "must_read": [],                # {path, authority_reason}
    "similar_implementations": [],  # {path, symbol, why}  (HEAVY: mirror to avoid breaking an invariant)
    "constraints": {"architectural": [], "invariant": [], "convention": []},  # arch: {constraint, evidence_ref}
    "rejected_alternatives": [],    # {category, alternative, broken_boundary}
    "risks": [],                    # {risk, severity, mitigation, acceptance_ref}
    "observations": [],             # {observation, changed_understanding(bool), evidence_ref}  (validation loop)
    "task_modes": [],               # advisory mirror of .forge/MODES; lock file is authoritative
    "runtime_observations": [],     # render/executable observations for render mode
    "debug_investigation": {},      # reproduction/hypotheses/root cause evidence for debug mode
    "stories": [],                  # multi-story checkpoints and final verification story
    "deferred": [],                 # tracked backlog / abandoned-but-recorded paths
    "forbidden_paths": [],          # globs the change must NOT touch (architecture/policy); verified at done
    "acceptance_criteria": [],      # {criterion, verify:{type,value}, evidence}
}
WORK_RE = re.compile(
    r"\b(implement|fix|refactor|add|build|create|write|change|update|migrat|"
    r"remove|delete|rename|optimi|debug|patch|integrat|wire|hook up|set up)\b",
    re.I,
)
WORK_KO = ("구현", "수정", "고쳐", "고치", "추가", "만들", "리팩", "변경", "바꿔",
           "바꾸", "삭제", "지워", "통합", "연결", "배선", "최적화", "패치")
QUESTION_KO_ENDINGS = ("나요", "까요", "가요", "은가", "는가", "ㄴ가", "?", "？")
HEAVY_RE = re.compile(r"\b(auth|payment|migrat|security|crypto|password|secret|"
                      r"billing|token|permission|delete)\b", re.I)
HEAVY_KO = ("보안", "결제", "인증", "마이그", "비밀번호", "권한", "토큰", "과금")


WEAK_EVIDENCE_EXACT = {
    "ok", "pass", "passed", "passes", "works", "worked", "done", "ran",
    "tested", "success", "successful", "all good", "looks good",
}

RESULT_SIGNAL_RE = re.compile(
    r"(->|exit\s*0|exit\s*1|return\s*code|returncode|ran\s+\d+\s+tests?|"
    r"\bOK\b|\bPASS(?:ED)?\b|\bFAIL(?:ED)?\b|HTTP\s+\d{3}|"
    r"no matches|matches|created|written|updated|artifact|screenshot|"
    r"\.(?:png|jpe?g|webp|json|log|txt|md|zip|html|css|js|ts|py)\b)",
    re.I,
)


def _evidence_quality_errors(item: dict, idx: int) -> list[str]:
    if item.get("deferred"):
        return []
    evidence = str(item.get("evidence") or "").strip()
    verify = item.get("verify") or {}
    verify_type = str(verify.get("type") or "").strip()
    norm = _norm(evidence)
    if norm in WEAK_EVIDENCE_EXACT or len(norm) < 8:
        return [f"acceptance_criteria[{idx}] has weak evidence; include command/artifact and observed result"]
    if verify_type in {"command", "test", "grep", "artifact", "stat"}:
        has_result_signal = RESULT_SIGNAL_RE.search(evidence) is not None
        has_specific_context = len(evidence) >= 48 and any(ch in evidence for ch in ("/", "\\", ".", ":"))
        if not (has_result_signal or has_specific_context):
            return [f"acceptance_criteria[{idx}] has weak evidence; include command/artifact and observed result"]
    return []


def _nonempty(v) -> bool:
    return isinstance(v, str) and v.strip() != ""

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()

def _inv_text(x) -> str:
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        return x.get("invariant") or x.get("text") or ""
    return ""

def _is_placeholder_risk(text) -> bool:
    """True if a 'risk' is really a non-declaration ('none', 'N/A.', 'No risks!', ...).
    Strip all non-alphanumerics so trailing punctuation/spacing can't smuggle one past."""
    core = re.sub(r"[^a-z0-9]", "", _norm(text))
    return core in {re.sub(r"[^a-z0-9]", "", p) for p in NO_RISK_PLACEHOLDERS}

def _forbidden_hits(spec: dict, root) -> list:
    """Edits (recorded by the PostToolUse hook in .forge/edits.txt) that match a
    forbidden_paths glob — i.e. the implementation touched an architecture/policy
    boundary the spec declared off-limits. Verifies no-conflict, not just declares."""
    pats = [p for p in spec.get("forbidden_paths", []) if isinstance(p, str) and p.strip()]
    if not pats or root is None:
        return []
    log = Path(root) / FORGE_DIR / "edits.txt"
    if not log.exists():
        return []
    try:
        edited = [ln.strip() for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    except Exception:
        return []
    hits = []
    for ed in edited:
        for pat in pats:
            if fnmatch.fnmatch(ed, pat) or (pat.strip("*/ ") and pat.strip("*/ ") in ed):
                hits.append((ed, pat))
                break
    return hits

def _effective_grade(spec: dict, root) -> str:
    """Grade drives enforcement depth. Read it from the scaffold-written
    `.forge/GRADE` (authoritative) so a model cannot silently downgrade in spec.json
    to skip checks. Falls back to spec.grade only when no GRADE file exists."""
    if root is not None:
        gf = Path(root) / FORGE_DIR / "GRADE"
        if gf.exists():
            try:
                g = gf.read_text(encoding="utf-8").strip().upper()
                if g in ("LIGHT", "STANDARD", "HEAVY"):
                    return g
            except Exception:
                pass
    return (spec.get("grade") or "STANDARD").upper()

def gate_spec(spec: dict, root=None) -> list[str]:
    """Grade-tiered. LIGHT pays almost nothing (token lever); STANDARD adds the
    core decision artifacts; HEAVY enforces the full Fable depth. `root` (when
    given) lets must_read paths be checked for real existence."""
    grade = _effective_grade(spec, root)
    e: list[str] = []

    # ---- ALL grades: minimal viable spec ----
    rg, raw = spec.get("restated_goal", ""), spec.get("raw_goal", "")
    if not _nonempty(rg):
        e.append("restated_goal is empty — restate intent as 'achieve X without Y, scoped to Z'.")
    elif _norm(rg) == _norm(raw) and _nonempty(raw):
        e.append("restated_goal is identical to the raw ask — you under-interpreted; normalize it.")

    good_acc = [c for c in spec.get("acceptance_criteria", [])
                if isinstance(c, dict) and _nonempty((c.get("verify") or {}).get("value"))]
    if not good_acc:
        e.append("acceptance_criteria needs >=1 entry with a runnable command/check in verify.value (not prose).")
    for i, c in enumerate(spec.get("acceptance_criteria", [])):
        if isinstance(c, dict):
            vt = ((c.get("verify") or {}).get("type") or "").strip().lower()
            if vt and vt not in ACC_TYPES:
                e.append(f"acceptance_criteria[{i}].verify.type '{vt}' not in {sorted(ACC_TYPES)}.")
    e.extend(forge_modes.gate_spec(spec, Path(root) if root is not None else None, FORGE_DIR))

    if grade == "LIGHT":
        return e

    # ---- STANDARD and HEAVY ----
    if not [x for x in spec.get("non_goals", []) if _nonempty(x)]:
        e.append("non_goals is empty — fence the over-broad version you are NOT doing.")

    for i, a in enumerate(spec.get("ambiguities", [])):
        if not isinstance(a, dict):
            e.append(f"ambiguities[{i}] must be an object {{question,resolution,authority}}.")
        elif not (_nonempty(a.get("question")) and _nonempty(a.get("resolution")) and _nonempty(a.get("authority"))):
            e.append(f"ambiguities[{i}] needs question + resolution + the authority that resolved it.")

    mr = [m for m in spec.get("must_read", [])
          if isinstance(m, dict) and _nonempty(m.get("path")) and _nonempty(m.get("authority_reason"))]
    if not mr:
        e.append("must_read needs >=1 file justified by authority (a contract/boundary it owns).")
    if root is not None:
        for i, m in enumerate(spec.get("must_read", [])):
            if isinstance(m, dict) and _nonempty(m.get("path")) and not m.get("external"):
                if not (Path(root) / m["path"]).exists():
                    e.append(f"must_read[{i}] path '{m['path']}' not found under root — read a real file or set external:true.")

    good_alts = []
    for i, a in enumerate(spec.get("rejected_alternatives", [])):
        if not isinstance(a, dict):
            e.append(f"rejected_alternatives[{i}] must be an object.")
            continue
        # The Fable pattern is "name a category + the boundary it breaks" — the
        # taxonomy is descriptive, not prescriptive. Require a non-empty category
        # (recommend the canonical four) but don't reject a valid label we didn't
        # enumerate; the broken_boundary is what carries the reasoning.
        cat = (a.get("category") or "").strip()
        if not cat:
            e.append(f"rejected_alternatives[{i}] needs a category (recommended: {sorted(ALT_CATEGORIES)}).")
        if _nonempty(a.get("alternative")) and _nonempty(a.get("broken_boundary")) and cat:
            good_alts.append(a)
    if len(good_alts) < 2:
        e.append("need >=2 rejected_alternatives, each with a valid category + the broken boundary it violates.")

    for i, r in enumerate(spec.get("risks", [])):
        if not isinstance(r, dict):
            e.append(f"risks[{i}] must be an object.")
            continue
        sev = (r.get("severity") or "").strip().lower()
        if not sev:
            e.append(f"risks[{i}] needs a severity ({sorted(SEVERITIES)}) — rate by blast radius, not effort.")
        elif sev not in SEVERITIES:
            e.append(f"risks[{i}].severity '{sev}' not in {sorted(SEVERITIES)}.")
        if not _nonempty(r.get("mitigation")):
            e.append(f"risks[{i}] needs a runnable mitigation, not 'be careful'.")
        if sev in {"high", "blocking"} and not _nonempty(r.get("acceptance_ref")):
            e.append(f"risks[{i}] is {sev} — mirror it into an acceptance criterion (acceptance_ref).")
    # The contract promises STANDARD+ declares at least one risk; enforce it so the two
    # never drift (a spec with no risk block is "I see no blast radius" — make it explicit).
    good_risks = [r for r in spec.get("risks", []) if isinstance(r, dict)
                  and _nonempty(r.get("risk")) and not _is_placeholder_risk(r.get("risk"))
                  and (r.get("severity") or "").strip().lower() in SEVERITIES
                  and _nonempty(r.get("mitigation"))]
    if not good_risks:
        e.append("risks needs >=1 {risk, severity, mitigation} — name a real blast-radius risk, not 'none'.")

    # STANDARD anchor: the cheapest constraint — what must NOT change. Without it,
    # later risk/alternative/acceptance decisions have nothing to anchor on.
    if not [x for x in ((spec.get("constraints") or {}).get("invariant") or []) if _nonempty(_inv_text(x))]:
        e.append("constraints.invariant needs >=1 — what must NOT change "
                 "(don't delete prior work / don't leak / don't weaken a check).")

    if grade != "HEAVY":
        return e

    # ---- HEAVY only: full Fable depth (constraint provenance, mirror, validation) ----
    cons = spec.get("constraints") or {}
    arch = cons.get("architectural") or []
    if not arch:
        e.append("HEAVY: constraints.architectural needs >=1 {constraint, evidence_ref}.")
    for i, c in enumerate(arch):
        if not (isinstance(c, dict) and _nonempty(c.get("constraint")) and _nonempty(c.get("evidence_ref"))):
            e.append(f"HEAVY: constraints.architectural[{i}] must be {{constraint, evidence_ref}} — pin what proved it.")

    si = [s for s in spec.get("similar_implementations", [])
          if isinstance(s, dict) and _nonempty(s.get("path")) and _nonempty(s.get("why"))]
    if not si:
        e.append("HEAVY: similar_implementations needs >=1 {path, why} to mirror — avoid breaking an invariant.")

    return e

def gate_done(spec: dict, root=None) -> list[str]:
    grade = _effective_grade(spec, root)
    e = gate_spec(spec, root)  # done implies spec still valid
    acc = [c for c in spec.get("acceptance_criteria", []) if isinstance(c, dict)]
    if not acc:
        e.append("no acceptance_criteria to verify.")
    for i, c in enumerate(acc):
        ev = c.get("evidence")
        if c.get("deferred") is True:
            # Strict `is True`: a truthy non-bool like "false" must NOT defer-and-skip.
            # Deferred is exempt from live evidence, but must NOT be a silent skip: it has
            # to record WHY it was dropped and what remains (the abandoned-task handoff).
            handoff = c.get("handoff") or c.get("reason") or (ev if isinstance(ev, str) else "")
            if not _nonempty(handoff):
                e.append(f"acceptance_criteria[{i}] is deferred with no handoff — record why it "
                         "was dropped and what remains (in evidence/handoff/reason).")
            continue
        if not _nonempty(ev):
            e.append(f"acceptance_criteria[{i}] has no evidence — run the check and cite live output (fail closed).")
        else:
            hit = next((m for m in FAKE_MARKERS if m in ev.lower()), None)
            if hit:
                e.append(f"acceptance_criteria[{i}] evidence reads as unfilled/fabricated ('{hit}') — "
                         "run it for real, or mark the criterion deferred with a handoff.")
            e.extend(_evidence_quality_errors(c, i))
    for ed, pat in _forbidden_hits(spec, root):
        e.append(f"edited '{ed}' which matches forbidden_paths '{pat}' — architecture/policy "
                 "conflict; revert that change or, if it is genuinely required, justify it by "
                 "moving the path out of forbidden_paths with a reason.")
    e.extend(forge_modes.gate_done(spec, Path(root) if root is not None else None, FORGE_DIR))
    if grade == "HEAVY":
        good_obs = [o for o in spec.get("observations", [])
                    if isinstance(o, dict) and _nonempty(o.get("observation"))]
        if not good_obs:
            e.append("HEAVY: validation loop unrecorded — log >=1 observation (what a read revealed, "
                     "with changed_understanding + evidence_ref) so decisions trace to evidence.")
    return e
