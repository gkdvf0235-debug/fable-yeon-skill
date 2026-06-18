#!/usr/bin/env python3
# Adapted and rebuilt distribution by ai.director_yeon. Thread ID: ai.director_yeon.
"""Claude PostToolUse adapter."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EDIT_TOOLS, edited_paths, is_off, project_root, read_payload, run_gate, session_id, tool_name  # noqa: E402


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
    paths = [path for path in edited_paths(payload) if ".forge/" not in path.replace("\\", "/")]
    if not paths:
        return 0
    log = Path(root) / ".forge" / "edits.txt"
    try:
        existing = set(log.read_text(encoding="utf-8").splitlines()) if log.exists() else set()
        new = [path for path in paths if path not in existing]
        if new:
            with log.open("a", encoding="utf-8") as handle:
                for path in new:
                    handle.write(path + "\n")
            args = ["loop", "--root", root, "--event", "edit"]
            for path in new:
                args += ["--path", path]
            run_gate(*args)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(f"fable-forge Claude post_tool_use error (failing open): {exc}\n")
        raise SystemExit(0)



