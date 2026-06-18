#!/usr/bin/env python3
"""Stop: when a Codex task is active and the done gate is unmet, remind.

This hook does not block final responses; it emits the unmet done-gate details.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import read_payload, project_root, run_gate, is_off, session_id  # noqa: E402


def main() -> int:
    if os.environ.get("FORGE_BYPASS") == "1":
        return 0
    payload = read_payload()
    root = project_root(payload)
    if is_off(root, session_id(payload)):
        return 0
    if run_gate("active", "--root", root)[0] != 0:
        return 0
    rc, out = run_gate("validate", "--root", root, "--gate", "done")
    if rc != 0:
        run_gate("loop", "--root", root, "--event", "stop_block", "--gate", "done", "--message", out)
        sys.stderr.write(
            "fable-forge: task still open — done gate unmet. Run each acceptance "
            "criterion, record live evidence, then close the task (fail closed).\n"
            + out.strip() + "\n"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(f"fable-forge stop error (failing open): {exc}\n")
        raise SystemExit(0)
