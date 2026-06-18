# Adapted and rebuilt distribution by ai.director_yeon. Thread ID: ai.director_yeon.
"""Shared helpers for the Claude adapter.

The adapter delegates gate semantics to the packaged shared core scripts and
keeps host-specific behavior limited to payload parsing and settings wiring.
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

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
GATE = PACKAGE_ROOT / "core" / "skills" / "falbe-yeon-codex" / "scripts" / "forge_gate.py"

EDIT_TOOLS = {"Edit", "Write", "MultiEdit"}
_PATCH_FILE_RE = re.compile(r"\*\*\* (?:Update|Add|Delete) File:\s*(.+)")


def read_payload() -> dict:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def project_root(payload: dict) -> str:
    root = payload.get("cwd") or payload.get("project_dir") or os.getcwd()
    try:
        return str(Path(root).resolve())
    except Exception:
        return str(root)


def run_gate(*args: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            [sys.executable, str(GATE), *args],
            capture_output=True,
            text=True,
            timeout=20,
            encoding="utf-8",
            errors="replace",
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except Exception as exc:
        return 0, f"fable gate skipped: {exc}"


def session_id(payload: dict) -> str:
    return str(payload.get("session_id") or payload.get("transcript_path") or "")


def is_off(root: str, sid: str = "") -> bool:
    args = ["runtime-state", "--root", str(root)]
    if sid:
        args += ["--sid", str(sid)]
    _, out = run_gate(*args)
    last = (out.strip().splitlines() or [""])[-1].strip().lower()
    return last != "on"


def tool_name(payload: dict) -> str:
    return str(payload.get("tool_name") or "")


def edited_paths(payload: dict) -> list[str]:
    tool_input = payload.get("tool_input") or {}
    out: list[str] = []
    for key in ("file_path", "path", "notebook_path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            out.append(value.strip())
    command = tool_input.get("command")
    if isinstance(command, str) and "*** " in command:
        out += [match.strip() for match in _PATCH_FILE_RE.findall(command)]
    return out


def edit_targets_blob(payload: dict) -> str:
    tool_input = payload.get("tool_input") or {}
    return " ".join(str(tool_input.get(k, "")) for k in ("file_path", "path", "notebook_path", "command"))



