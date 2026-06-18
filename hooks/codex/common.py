"""Shared helpers for Falbe Yeon Codex hooks.

Codex delivers a JSON stdin payload with tool_name/tool_input/cwd and accepts
exit code 2 plus stderr as a tool-call block. These hooks are intentionally
thin: they route to the bundled forge_gate.py only when the project gate is on.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# hooks/<file>.py -> plugin root -> skills/falbe-yeon-codex/scripts/forge_gate.py
GATE = Path(__file__).resolve().parents[2] / "skills" / "falbe-yeon-codex" / "scripts" / "forge_gate.py"

# Codex reports edits primarily as apply_patch. Keep Edit/Write for compatible
# tool surfaces, but do not include unrelated notebook or string-replace names.
EDIT_TOOLS = {"apply_patch", "Edit", "Write"}
SHELL_TOOLS = {"shell_command", "functions.shell_command", "Bash", "bash", "Shell"}

_PATCH_FILE_RE = re.compile(r"\*\*\* (?:Update|Add|Delete) File:\s*(.+)")


def read_payload() -> dict:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def project_root(payload: dict) -> str:
    r = payload.get("cwd") or os.getcwd()
    try:
        return str(Path(r).resolve())
    except Exception:
        return str(r)


def run_gate(*args: str) -> tuple[int, str]:
    try:
        p = subprocess.run([sys.executable, str(GATE), *args],
                           capture_output=True, text=True, timeout=20,
                           encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as exc:
        return 0, f"forge gate skipped: {exc}"


def session_id(payload: dict) -> str:
    return str(payload.get("session_id") or "")


def is_off(root, sid: str = "") -> bool:
    """Runtime gate is disabled unless raw state and a fresh lease are both valid.
    Delegates to the gate's `runtime-state` command so lease validation has one SSOT.
    Fails open if state can't be determined."""
    args = ["runtime-state", "--root", str(root)]
    if sid:
        args += ["--sid", str(sid)]
    _, out = run_gate(*args)
    last = (out.strip().splitlines() or [""])[-1].strip().lower()
    return last != "on"


def tool_name(payload: dict) -> str:
    return payload.get("tool_name", "") or ""


def edited_paths(payload: dict) -> list[str]:
    """Real file paths an edit touches.

    Codex apply_patch paths are parsed from the patch header lines in
    tool_input.command. Edit/Write compatibility payloads may provide file_path.
    """
    ti = payload.get("tool_input") or {}
    out: list[str] = []
    for k in ("file_path", "path", "notebook_path"):
        v = ti.get(k)
        if isinstance(v, str) and v.strip():
            out.append(v.strip())
    cmd = ti.get("command")
    if isinstance(cmd, str) and "*** " in cmd:
        out += [m.strip() for m in _PATCH_FILE_RE.findall(cmd)]
    return out


def edit_targets_blob(payload: dict) -> str:
    """A single string covering every path/command an edit references — used only
    for the cheap `.forge/` self-authoring exemption."""
    ti = payload.get("tool_input") or {}
    return " ".join(str(ti.get(k, "")) for k in ("file_path", "path", "notebook_path", "command"))


def shell_command_text(payload: dict) -> str:
    ti = payload.get("tool_input") or {}
    for key in ("command", "cmd", "script"):
        value = ti.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""
