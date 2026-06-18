#!/usr/bin/env python3
"""Install/uninstall Fable Yeon Skill Codex hooks into CODEX_HOME/hooks.json.

The merge is additive and preserves existing hooks. The gate itself defaults off;
installing hooks does not start gating ordinary work.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

EVENTS = ("UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop")
PRE_TOOL_MATCHER = r"apply_patch|Edit|Write|shell_command|functions\.shell_command|Bash|bash|Shell"
INSTALL_PLAN = (
    ("UserPromptSubmit", None, "user_prompt_submit.py"),
    ("PreToolUse", PRE_TOOL_MATCHER, "pre_tool_use.py"),
    ("PostToolUse", "apply_patch|Edit|Write", "post_tool_use.py"),
    ("Stop", None, "stop.py"),
)


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def hooks_json_path() -> Path:
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    return home / "hooks.json"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def hook_command(name: str) -> dict:
    hook_path = plugin_root() / "hooks" / "codex" / name
    return {
        "type": "command",
        "command": f'"{sys.executable}" "{hook_path}"',
        "timeout": 20,
        "statusMessage": "Fable Yeon Skill (Codex)",
    }


def hook_group(matcher: str | None, name: str) -> dict:
    group = {"hooks": [hook_command(name)]}
    if matcher:
        group["matcher"] = matcher
    return group


def planned_groups() -> list[tuple[str, dict]]:
    return [(event, hook_group(matcher, name)) for event, matcher, name in INSTALL_PLAN]


def strip_ours(hooks: dict) -> None:
    marker = str(plugin_root())
    for event in EVENTS:
        kept = []
        for group in hooks.get(event, []):
            group = dict(group)
            group["hooks"] = [
                hook for hook in group.get("hooks", [])
                if marker not in str(hook.get("command", ""))
            ]
            if group["hooks"]:
                kept.append(group)
        if kept:
            hooks[event] = kept
        else:
            hooks.pop(event, None)


def install(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    config = load_json(path)
    hooks = config.setdefault("hooks", {})
    strip_ours(hooks)
    for event, group in planned_groups():
        hooks.setdefault(event, []).append(group)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"falbe-yeon-codex: installed hooks -> {path}")
    print("falbe-yeon-codex: gate default is OFF; use $falbe-yeon-codex, `fable gate on`, `페이블 게이트 on`, or `미토스 게이트 on` to enable.")


def uninstall(path: Path) -> None:
    config = load_json(path)
    hooks = config.setdefault("hooks", {})
    strip_ours(hooks)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"falbe-yeon-codex: removed hooks -> {path}")


def dry_run(path: Path) -> int:
    print(f"falbe-yeon-codex: dry-run only; no files will be written")
    print(f"  hooks_json: {path}")
    print(f"  plugin_root: {plugin_root()}")
    for event, matcher, name in INSTALL_PLAN:
        matcher_text = f" matcher={matcher}" if matcher else ""
        print(f"  would install {event}{matcher_text}: {plugin_root() / 'hooks' / 'codex' / name}")
    return 0


def check(path: Path) -> int:
    config = load_json(path)
    hooks = config.get("hooks", {}) if isinstance(config, dict) else {}
    missing = []
    for event, matcher, name in INSTALL_PLAN:
        expected_path = str(plugin_root() / "hooks" / "codex" / name)
        found = False
        for group in hooks.get(event, []):
            if matcher and group.get("matcher") != matcher:
                continue
            for hook in group.get("hooks", []):
                if expected_path in str(hook.get("command", "")):
                    found = True
                    break
            if found:
                break
        status = "installed" if found else "missing"
        print(f"falbe-yeon-codex: {event}/{name}: {status}")
        if not found:
            missing.append(f"{event}/{name}")
    if missing:
        print(f"falbe-yeon-codex: check failed; missing {', '.join(missing)}")
        return 1
    print("falbe-yeon-codex: check passed; all hooks for this plugin are installed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Install, inspect, or remove Fable Yeon Skill Codex hooks.")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--uninstall", action="store_true", help="remove only hooks installed by this plugin")
    actions.add_argument("--dry-run", action="store_true", help="show the hook entries that would be installed without writing hooks.json")
    actions.add_argument("--check", action="store_true", help="inspect hooks.json and report whether this plugin's hooks are installed")
    parser.add_argument("--hooks-json", type=Path, default=hooks_json_path())
    args = parser.parse_args()
    if args.dry_run:
        return dry_run(args.hooks_json)
    if args.check:
        return check(args.hooks_json)
    if args.uninstall:
        uninstall(args.hooks_json)
    else:
        install(args.hooks_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
