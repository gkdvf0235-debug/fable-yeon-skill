#!/usr/bin/env python3
"""Small Codex-facing wrapper around forge_gate.py.

The raw gate remains the SSOT. This wrapper only makes the skill workflow short:
start -> validate-spec -> validate-done -> close/off/status.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

GATE = Path(__file__).resolve().with_name("forge_gate.py")


def run_gate(*args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        [sys.executable, str(GATE), *args],
        text=True,
        capture_output=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    text = (proc.stdout or "") + (proc.stderr or "")
    if text:
        print(text, end="" if text.endswith("\n") else "\n")
    if check and proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc


def root_arg(root: str | None) -> str:
    return str(Path(root or ".").resolve())


def cmd_start(args: argparse.Namespace) -> int:
    root = root_arg(args.root)
    goal = args.goal.strip()
    if not goal:
        raise SystemExit("falbe-yeon-codex: --goal is required.")
    run_gate("toggle", "--root", root, "--scope", "project", "--set", "on", check=True)
    run_gate("scaffold", "--root", root, "--goal", goal, check=True)
    run_gate("lease", "--root", root, "issue", check=True)
    run_gate("contract", "--root", root, check=True)
    return 0


def cmd_off(args: argparse.Namespace) -> int:
    run_gate("toggle", "--root", root_arg(args.root), "--scope", "project", "--set", "off", check=True)
    return 0


def cmd_on(args: argparse.Namespace) -> int:
    run_gate("toggle", "--root", root_arg(args.root), "--scope", "project", "--set", "on", check=True)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = root_arg(args.root)
    run_gate("state", "--root", root, "--verbose")
    run_gate("runtime-state", "--root", root, "--verbose")
    run_gate("status", "--root", root)
    return 0


def cmd_runtime_state(args: argparse.Namespace) -> int:
    return run_gate("runtime-state", "--root", root_arg(args.root), "--verbose").returncode


def cmd_validate_spec(args: argparse.Namespace) -> int:
    root = root_arg(args.root)
    run_gate("lease", "--root", root, "renew")
    return run_gate("validate", "--root", root, "--gate", "spec").returncode


def cmd_validate_done(args: argparse.Namespace) -> int:
    root = root_arg(args.root)
    run_gate("lease", "--root", root, "renew")
    return run_gate("validate", "--root", root, "--gate", "done").returncode


def cmd_close(args: argparse.Namespace) -> int:
    root = root_arg(args.root)
    done = run_gate("validate", "--root", root, "--gate", "done")
    if done.returncode != 0:
        return done.returncode
    close = run_gate("close", "--root", root)
    if close.returncode == 0:
        run_gate("toggle", "--root", root, "--scope", "project", "--set", "off")
    return close.returncode


def cmd_heartbeat(args: argparse.Namespace) -> int:
    root = root_arg(args.root)
    return run_gate("lease", "--root", root, "renew").returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex_fable_gate.py")
    parser.add_argument("--root", default=".", help="Project root. Defaults to the current directory.")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start")
    start.add_argument("--goal", required=True)
    start.set_defaults(fn=cmd_start)

    sub.add_parser("on").set_defaults(fn=cmd_on)
    sub.add_parser("off").set_defaults(fn=cmd_off)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("runtime-state").set_defaults(fn=cmd_runtime_state)
    sub.add_parser("validate-spec").set_defaults(fn=cmd_validate_spec)
    sub.add_parser("validate-done").set_defaults(fn=cmd_validate_done)
    sub.add_parser("close").set_defaults(fn=cmd_close)
    sub.add_parser("heartbeat").set_defaults(fn=cmd_heartbeat)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
