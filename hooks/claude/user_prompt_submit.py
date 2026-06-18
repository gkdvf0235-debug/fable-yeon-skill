#!/usr/bin/env python3
# Adapted and rebuilt distribution by ai.director_yeon. Thread ID: ai.director_yeon.
"""Claude UserPromptSubmit adapter for explicit gate toggle commands.

This hook does not auto-start ordinary prompts. It only handles explicit
Fable/Mythos gate commands so the hard gate stays scoped to deliberate use.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import project_root, read_payload, run_gate, session_id  # noqa: E402

SCOPE_SYNONYMS = {
    "session": "session", "here": "session", "this": "session", "chat": "session", "s": "session",
    "project": "project", "dir": "project", "repo": "project", "folder": "project", "p": "project",
    "machine": "machine", "all": "machine", "desktop": "machine", "global": "machine",
    "everywhere": "machine", "m": "machine",
}

_TOGGLE_RE = re.compile(
    r"^/?(?:forge|fable(?:\s+gate)?|mythos(?:\s+gate)?|페이블(?:\s+게이트)?|미토스(?:\s+게이트)?|falble-yeon-claude|falbe-yeon-codex)[:\s]+"
    r"(on|off|status|stop|start)\b\s*(.*)$",
    re.I | re.S,
)


def _parse_toggle(prompt: str):
    low = prompt.strip().lower()
    if low in (
        "forge?", "/forge?", "fable gate?", "/fable gate?", "mythos gate?", "/mythos gate?",
        "페이블?", "/페이블?", "페이블 게이트?", "/페이블 게이트?",
        "미토스?", "/미토스?", "미토스 게이트?", "/미토스 게이트?",
    ):
        return ("status", "project")
    match = _TOGGLE_RE.match(low)
    if not match:
        return None
    verb = {"stop": "off", "start": "on"}.get(match.group(1), match.group(1))
    rest = match.group(2).strip()
    if not rest:
        return (verb, "project")
    if rest in SCOPE_SYNONYMS:
        return (verb, SCOPE_SYNONYMS[rest])
    return ("invalid", rest)


def emit_block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))


def main() -> int:
    if os.environ.get("FORGE_BYPASS") == "1":
        return 0
    payload = read_payload()
    root = project_root(payload)
    prompt = str(payload.get("prompt") or "").strip()
    sid = session_id(payload)
    parsed = _parse_toggle(prompt)
    if not parsed:
        return 0

    verb, scope = parsed
    if verb == "invalid":
        emit_block(
            f"fable-forge: unknown scope '{scope}'. Use none/project, here/session, or all/machine."
        )
        return 0
    if verb == "status":
        raw = run_gate("state", "--root", root, "--sid", sid, "--verbose")[1].strip()
        runtime = run_gate("runtime-state", "--root", root, "--sid", sid, "--verbose")[1].strip()
        emit_block("fable-forge: " + raw + " | " + runtime)
        return 0
    if scope == "session" and not sid:
        emit_block(
            f"fable-forge: no session id available; use 'forge {verb} project' or 'forge {verb} all'."
        )
        return 0
    run_gate("toggle", "--root", root, "--scope", scope, "--set", verb, "--sid", sid)
    emit_block(
        f"fable-forge: gate {verb.upper()} [{scope}]. "
        + run_gate("state", "--root", root, "--sid", sid, "--verbose")[1].strip()
        + " | "
        + run_gate("runtime-state", "--root", root, "--sid", sid, "--verbose")[1].strip()
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(f"fable-forge Claude user_prompt_submit error (failing open): {exc}\n")
        raise SystemExit(0)
