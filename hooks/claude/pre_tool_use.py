#!/usr/bin/env python3
# Adapted and rebuilt distribution by ai.director_yeon. Thread ID: ai.director_yeon.
"""Claude PreToolUse adapter."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (EDIT_TOOLS, edit_targets_blob, edited_paths, is_off,  # noqa: E402
                    project_root, read_payload, run_gate, session_id, tool_name)


def _is_forge(path: str) -> bool:
    return ".forge/" in path.replace("\\", "/") or path.rstrip("/\\").endswith(".forge")


def main() -> int:
    if os.environ.get("FORGE_BYPASS") == "1":
        return 0
    payload = read_payload()
    if tool_name(payload) not in EDIT_TOOLS:
        return 0
    root = project_root(payload)
    if is_off(root, session_id(payload)):
        return 0
    if not edit_targets_blob(payload).strip():
        return 0
    if run_gate("active", "--root", root)[0] != 0:
        return 0
    paths = edited_paths(payload)
    if paths and all(_is_forge(path) for path in paths):
        run_gate("loop", "--root", root, "--event", "spec_edit")
        return 0
    rc, out = run_gate("validate", "--root", root, "--gate", "spec")
    if rc != 0:
        run_gate("loop", "--root", root, "--event", "pre_block", "--gate", "spec", "--message", out)
        sys.stderr.write(
            "fable-forge: implementation blocked because SPEC gate is not satisfied.\n"
            "Fill .forge/spec.json, validate SPEC, then retry the edit.\n\n"
            + out.strip()
            + "\n"
        )
        return 2
    run_gate("loop", "--root", root, "--event", "pre_allow", "--gate", "spec")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(f"fable-forge Claude pre_tool_use error (failing open): {exc}\n")
        raise SystemExit(0)



