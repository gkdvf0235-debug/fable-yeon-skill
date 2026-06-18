#!/usr/bin/env python3
# Adapted and rebuilt distribution by ai.director_yeon. Thread ID: ai.director_yeon.
"""Claude Stop adapter."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import is_off, project_root, read_payload, run_gate, session_id  # noqa: E402


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
            "fable-forge: task still open because DONE gate is unmet. "
            "Run acceptance checks, record evidence, then close.\n"
            + out.strip()
            + "\n"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(f"fable-forge Claude stop error (failing open): {exc}\n")
        raise SystemExit(0)



