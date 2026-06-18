#!/usr/bin/env python3
"""PostToolUse: record which files an edit touched, so the done gate can VERIFY
the implementation did not conflict with the architecture/policy the spec declared
(forbidden_paths) — not just that the spec declared them.

Append-only, deduped, hook-side (zero model tokens). Records only while a task is
active. Never blocks (observational). Codex-focused."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import read_payload, project_root, run_gate, tool_name, edited_paths, is_off, session_id, EDIT_TOOLS  # noqa: E402


def main() -> int:
    if os.environ.get("FORGE_BYPASS") == "1":
        return 0
    payload = read_payload()
    if tool_name(payload) not in EDIT_TOOLS:
        return 0
    root = project_root(payload)
    if is_off(root, session_id(payload)):
        return 0
    if run_gate("active", "--root", root)[0] != 0:
        return 0
    paths = [p for p in edited_paths(payload) if ".forge/" not in p]
    if not paths:
        return 0
    log = Path(root) / ".forge" / "edits.txt"
    try:
        existing = set(log.read_text(encoding="utf-8").splitlines()) if log.exists() else set()
        new = [p for p in paths if p not in existing]
        if new:
            with log.open("a", encoding="utf-8") as f:
                for p in new:
                    f.write(p + "\n")
            loop_args = ["loop", "--root", root, "--event", "edit"]
            for p in new:
                loop_args += ["--path", p]
            run_gate(*loop_args)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(f"fable-forge post_tool_use error (failing open): {exc}\n")
        raise SystemExit(0)
