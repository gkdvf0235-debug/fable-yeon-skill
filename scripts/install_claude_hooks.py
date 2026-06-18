#!/usr/bin/env python3
"""Install/uninstall Fable Yeon Skill Claude hooks and skill files.

The merge is additive and preserves existing hook groups. Installing hooks does
not turn the gate on; runtime enforcement still requires project state, an
active task, and a valid lease. The installer also copies the Claude-facing
skill into ~/.claude/skills by default so Claude Code can discover the workflow
instructions, not just the hook commands.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

EVENTS = ("UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop")
SKILL_NAME = "falble-yeon-claude"
INSTALL_PLAN = (
    ("UserPromptSubmit", None, "user_prompt_submit.py"),
    ("PreToolUse", "Edit|Write|MultiEdit", "pre_tool_use.py"),
    ("PostToolUse", "Edit|Write|MultiEdit", "post_tool_use.py"),
    ("Stop", None, "stop.py"),
)


def package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def default_skills_dir() -> Path:
    return Path.home() / ".claude" / "skills"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def hook_command(name: str) -> dict:
    hook_path = package_root() / "hooks" / "claude" / name
    return {
        "type": "command",
        "command": f'"{sys.executable}" "{hook_path}"',
        "timeout": 20,
    }


def hook_group(matcher: str | None, name: str) -> dict:
    group = {"hooks": [hook_command(name)]}
    if matcher:
        group["matcher"] = matcher
    return group


def planned_groups() -> list[tuple[str, dict]]:
    return [(event, hook_group(matcher, name)) for event, matcher, name in INSTALL_PLAN]


def source_skill_dir() -> Path:
    return package_root() / "skills" / SKILL_NAME


def target_skill_dir(skills_dir: Path) -> Path:
    return skills_dir / SKILL_NAME


def copy_skill(skills_dir: Path) -> None:
    src = source_skill_dir()
    dst = target_skill_dir(skills_dir)
    if not src.exists():
        raise SystemExit(f"falble-yeon-claude: missing source skill folder: {src}")
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def skill_installed(skills_dir: Path) -> bool:
    dst = target_skill_dir(skills_dir)
    return (dst / "SKILL.md").exists() and (dst / "read.md").exists()


def strip_ours(hooks: dict) -> None:
    marker = str(package_root())
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


def install(path: Path, skills_dir: Path, hooks_only: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    config = load_json(path)
    hooks = config.setdefault("hooks", {})
    strip_ours(hooks)
    for event, group in planned_groups():
        hooks.setdefault(event, []).append(group)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"falble-yeon-claude: installed hooks -> {path}")
    if not hooks_only:
        copy_skill(skills_dir)
        print(f"falble-yeon-claude: installed skill -> {target_skill_dir(skills_dir)}")
    print("falble-yeon-claude: gate default is OFF; use the skill start command or explicit fable/mythos gate commands.")


def uninstall(path: Path) -> None:
    config = load_json(path)
    hooks = config.setdefault("hooks", {})
    strip_ours(hooks)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"falble-yeon-claude: removed hooks -> {path}")


def dry_run(path: Path, skills_dir: Path, hooks_only: bool = False) -> int:
    print("falble-yeon-claude: dry-run only; no files will be written")
    print(f"  settings_json: {path}")
    print(f"  skills_dir: {skills_dir}")
    print(f"  package_root: {package_root()}")
    if not hooks_only:
        print(f"  would install skill: {source_skill_dir()} -> {target_skill_dir(skills_dir)}")
    for event, matcher, name in INSTALL_PLAN:
        matcher_text = f" matcher={matcher}" if matcher else ""
        print(f"  would install {event}{matcher_text}: {package_root() / 'hooks' / 'claude' / name}")
    return 0


def check(path: Path, skills_dir: Path, hooks_only: bool = False) -> int:
    config = load_json(path)
    hooks = config.get("hooks", {}) if isinstance(config, dict) else {}
    missing = []
    if not hooks_only:
        installed = skill_installed(skills_dir)
        status = "installed" if installed else "missing"
        print(f"falble-yeon-claude: skill/{SKILL_NAME}: {status}")
        if not installed:
            missing.append(f"skill/{SKILL_NAME}")
    for event, matcher, name in INSTALL_PLAN:
        expected_path = str(package_root() / "hooks" / "claude" / name)
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
        print(f"falble-yeon-claude: {event}/{name}: {status}")
        if not found:
            missing.append(f"{event}/{name}")
    if missing:
        print(f"falble-yeon-claude: check failed; missing {', '.join(missing)}")
        return 1
    print("falble-yeon-claude: check passed; all hooks for this package are installed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Install, inspect, or remove Fable Yeon Skill Claude hooks and skill files.")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--uninstall", action="store_true", help="remove only hooks installed by this package")
    actions.add_argument("--dry-run", action="store_true", help="show hook entries without writing settings")
    actions.add_argument("--check", action="store_true", help="inspect settings and report whether hooks and skill are installed")
    parser.add_argument("--settings-json", type=Path, default=default_settings_path())
    parser.add_argument("--skills-dir", type=Path, default=default_skills_dir())
    parser.add_argument("--hooks-only", action="store_true", help="install/check only hooks, not the Claude skill folder")
    args = parser.parse_args()
    if args.dry_run:
        return dry_run(args.settings_json, args.skills_dir, args.hooks_only)
    if args.check:
        return check(args.settings_json, args.skills_dir, args.hooks_only)
    if args.uninstall:
        uninstall(args.settings_json)
    else:
        install(args.settings_json, args.skills_dir, args.hooks_only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
