#!/usr/bin/env python3
"""Falbe Yeon Codex state, lease, and loop persistence helpers."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
import secrets
import sys
import time
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

FORGE_DIR = ".forge"
SPEC_NAME = "spec.json"
ACTIVE_NAME = "ACTIVE"
LOOP_NAME = "loop.json"
LEASE_NAME = "lease.json"
DEFAULT_LEASE_TTL_SECONDS = 300
SCOPES = ("session", "project", "machine")

def spec_path(root: Path) -> Path:
    return root / FORGE_DIR / SPEC_NAME

def active_path(root: Path) -> Path:
    return root / FORGE_DIR / ACTIVE_NAME

def loop_path(root: Path) -> Path:
    return root / FORGE_DIR / LOOP_NAME

def lease_path(root: Path) -> Path:
    return root / FORGE_DIR / LEASE_NAME

def _machine_dir() -> Path:
    # Must NOT be any project's <root>/.forge, or project state could collide with
    # machine state. Use the XDG config dir.
    if os.environ.get("FORGE_HOME"):
        return Path(os.environ["FORGE_HOME"])
    base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(base) / "forge"

def _read_state(p: Path):
    try:
        if p.exists():
            v = p.read_text(encoding="utf-8").strip().lower()
            if v in ("on", "off"):
                return v
    except Exception:
        pass
    return None

def _safe_sid(sid) -> str:
    # sid is an arbitrary runtime string — never use it as a path directly (/, .., abs
    # would escape the sessions dir). Hash to a fixed, collision-resistant, escape-proof
    # filename component (a plain char-strip would collide, e.g. "a/b" vs "a_b").
    return hashlib.sha256(str(sid).encode("utf-8", "replace")).hexdigest()[:32]

def _session_state_path(root, sid) -> Path:
    return Path(root) / FORGE_DIR / "sessions" / _safe_sid(sid)

def _scope_states(root, sid):
    """(session, project, machine) raw state, each 'on' / 'off' / None (inherit)."""
    sess = _read_state(_session_state_path(root, sid)) if sid else None
    proj = _read_state(Path(root) / FORGE_DIR / "STATE")
    if proj is None and (Path(root) / FORGE_DIR / "OFF").exists():
        proj = "off"  # back-compat with the old binary OFF marker
    mach = _read_state(_machine_dir() / "STATE")
    return sess, proj, mach

def effective_state(root, sid=None) -> str:
    """Resolve on/off by precedence: session > project > machine > default OFF."""
    sess, proj, mach = _scope_states(root, sid)
    for s in (sess, proj, mach):
        if s:
            return s
    # Codex plugin mode defaults to OFF. The skill or an explicit hook command
    # turns a project/session on, which prevents ordinary work from being gated.
    return "off"

def load_spec(root: Path):
    p = spec_path(root)
    if not p.exists():
        return None, f"no spec at {p}"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # malformed JSON must read as a gate failure, not crash
        return None, f"spec.json is not valid JSON: {exc}"
    if not isinstance(data, dict):
        return None, "spec.json must be a JSON object"
    return data, None

def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _now_epoch() -> int:
    return int(time.time())

def _iso_from_epoch(value: int) -> str:
    return datetime.fromtimestamp(value, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _lease_ttl() -> int:
    try:
        return max(30, int(os.environ.get("FORGE_LEASE_TTL_SECONDS", DEFAULT_LEASE_TTL_SECONDS)))
    except Exception:
        return DEFAULT_LEASE_TTL_SECONDS

def _boot_marker() -> str:
    """Best-effort reboot marker. If it cannot be determined, use a stable
    fallback instead of crashing; lease validation remains fail-open elsewhere."""
    try:
        if sys.platform.startswith("win"):
            import ctypes
            uptime_ms = ctypes.windll.kernel32.GetTickCount64()
            boot_epoch = int(time.time() - (uptime_ms / 1000))
            return f"win:{boot_epoch // 60}"
        stat = Path("/proc/stat")
        if stat.exists():
            for line in stat.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("btime "):
                    return f"unix:{line.split()[1]}"
    except Exception:
        pass
    return f"unknown:{os.environ.get('COMPUTERNAME') or os.environ.get('HOSTNAME') or 'host'}"

def _global_disable_path() -> Path:
    return Path.home() / ".codex" / "fable-disable"

def _global_disabled() -> bool:
    return os.environ.get("FORGE_DISABLE") == "1" or _global_disable_path().exists()

def _read_lease(root: Path) -> tuple[dict | None, str]:
    try:
        p = lease_path(root)
        if not p.exists():
            return None, "missing"
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None, "malformed"
        return data, ""
    except Exception:
        return None, "malformed"

def _write_lease(root: Path, data: dict) -> None:
    fdir = root / FORGE_DIR
    fdir.mkdir(parents=True, exist_ok=True)
    lease_path(root).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def issue_lease(root: Path, sid: str = "", ttl: int | None = None) -> dict:
    now = _now_epoch()
    ttl = ttl or _lease_ttl()
    data = {
        "version": 1,
        "skill": "falbe-yeon-codex",
        "status": "on",
        "root": str(root.resolve()),
        "session_id_hash": _safe_sid(sid) if sid else "",
        "nonce": secrets.token_urlsafe(18),
        "created_at": _iso_from_epoch(now),
        "heartbeat_at": _iso_from_epoch(now),
        "expires_at": _iso_from_epoch(now + ttl),
        "expires_epoch": now + ttl,
        "ttl_seconds": ttl,
        "boot_marker": _boot_marker(),
    }
    _write_lease(root, data)
    return data

def clear_lease(root: Path) -> None:
    try:
        lease_path(root).unlink(missing_ok=True)
    except Exception:
        pass

def lease_status(root: Path, sid: str = "") -> tuple[bool, str]:
    if _global_disabled():
        return False, "global-disable"
    if effective_state(root, sid) != "on":
        return False, "state-off"
    data, err = _read_lease(root)
    if err:
        return False, f"lease-{err}"
    try:
        if data.get("status") != "on":
            return False, "lease-status-off"
        if data.get("skill") != "falbe-yeon-codex":
            return False, "lease-skill-mismatch"
        if str(Path(data.get("root", "")).resolve()) != str(Path(root).resolve()):
            return False, "lease-root-mismatch"
        if data.get("boot_marker") != _boot_marker():
            return False, "lease-rebooted"
        if int(data.get("expires_epoch", 0)) <= _now_epoch():
            return False, "lease-expired"
    except Exception:
        return False, "lease-invalid"
    return True, "lease-valid"

def runtime_state(root: Path, sid: str = "") -> str:
    ok, _ = lease_status(root, sid)
    return "on" if ok else "off"

def _active_goal(root: Path) -> str:
    try:
        return active_path(root).read_text(encoding="utf-8").strip()
    except Exception:
        return ""

def _base_loop(root: Path) -> dict:
    return {
        "version": 1,
        "status": "active" if active_path(root).exists() else "inactive",
        "phase": "SPEC",
        "goal": _active_goal(root),
        "last_failure": None,
        "next_action": "Fill .forge/spec.json until the SPEC gate passes.",
        "edited_paths": [],
        "events": [],
        "created_at": _now_utc(),
        "updated_at": _now_utc(),
    }

def _load_loop(root: Path) -> dict:
    p = loop_path(root)
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                base = _base_loop(root)
                base.update(data)
                base.setdefault("edited_paths", [])
                base.setdefault("events", [])
                return base
        except Exception:
            pass
    return _base_loop(root)

def _write_loop(root: Path, data: dict) -> None:
    fdir = root / FORGE_DIR
    fdir.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _now_utc()
    loop_path(root).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def _message_items(message: str) -> list[str]:
    items: list[str] = []
    for line in (message or "").splitlines():
        s = line.strip()
        if s.startswith("- "):
            items.append(s[2:].strip())
        elif s.startswith("  - "):
            items.append(s[4:].strip())
    if not items and message:
        items = [line.strip() for line in message.splitlines() if line.strip()][:5]
    return items[:20]

def _bounded_events(events: list[dict]) -> list[dict]:
    return events[-50:]

def record_loop_event(root: Path, event: str, *, gate: str = "", message: str = "",
                      paths: list[str] | None = None, status: str = "",
                      next_action: str = "") -> None:
    """Update .forge/loop.json while a task is active.

    The loop file is a local artifact only. It is never printed into context unless
    `status` is requested, and hooks call this only after gate ON + active checks.
    """
    if event != "scaffold" and not active_path(root).exists():
        return
    data = _load_loop(root)
    data["status"] = status or ("active" if active_path(root).exists() else data.get("status", "inactive"))
    data["goal"] = data.get("goal") or _active_goal(root)

    if event in {"validate_pass", "pre_allow"}:
        if gate == "spec":
            data["phase"] = "IMPLEMENT"
            data["next_action"] = next_action or "Implement the scoped change and preserve declared invariants."
        elif gate == "done":
            data["phase"] = "DONE_READY"
            data["next_action"] = next_action or "Close the task or turn the gate off after reporting evidence."
        data["last_failure"] = None
    elif event in {"validate_block", "pre_block", "stop_block"}:
        items = _message_items(message)
        data["last_failure"] = {
            "gate": gate or "unknown",
            "items": items,
            "at": _now_utc(),
        }
        if gate == "done":
            data["phase"] = "VERIFY"
            data["next_action"] = next_action or "Record live evidence for each acceptance criterion, then close."
        else:
            data["phase"] = "SPEC"
            data["next_action"] = next_action or "Fix .forge/spec.json before implementation edits."
    elif event == "spec_edit":
        data["phase"] = "SPEC"
        data["next_action"] = next_action or "Run the SPEC gate; implement only after it passes."
    elif event == "edit":
        edited = data.setdefault("edited_paths", [])
        for path in paths or []:
            if path and path not in edited:
                edited.append(path)
        data["phase"] = "IMPLEMENT"
        data["next_action"] = next_action or "Run acceptance checks and record evidence in .forge/spec.json."
    elif event == "close":
        data["status"] = status or "closed"
        data["phase"] = "CLOSED"
        data["next_action"] = next_action or "Gate can remain off until the next explicit Fable task."
    elif event == "scaffold":
        data = _base_loop(root)

    event_record = {
        "event": event,
        "gate": gate,
        "paths": paths or [],
        "message": (message or "")[:2000],
        "at": _now_utc(),
    }
    data["events"] = _bounded_events([*data.get("events", []), event_record])
    _write_loop(root, data)
