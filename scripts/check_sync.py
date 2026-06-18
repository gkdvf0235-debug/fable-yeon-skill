#!/usr/bin/env python3
"""Check Fable Yeon Skill Codex runtime sync.

This script treats the stable plugin package as the runtime authority. It does
not compare against a desktop/source checkout by default.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import install_codex_hooks

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

SKILL_NAME = "falbe-yeon-codex"


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_mirror() -> Path:
    return Path.home() / ".agents" / "skills" / SKILL_NAME


def _skip_file(path: Path) -> bool:
    return "__pycache__" in path.parts or path.suffix == ".pyc"


def _files(base: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(base.rglob("*")):
        if path.is_file() and not _skip_file(path):
            rel = path.relative_to(base).as_posix()
            out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def check_skill_mirror(mirror: Path) -> bool:
    source = plugin_root() / "skills" / SKILL_NAME
    if not mirror.exists():
        print(f"skill mirror: missing ({mirror})")
        return False
    source_files = _files(source)
    mirror_files = _files(mirror)
    if source_files == mirror_files:
        print(f"skill mirror: ok ({mirror})")
        return True

    missing = sorted(set(source_files) - set(mirror_files))
    extra = sorted(set(mirror_files) - set(source_files))
    changed = sorted(k for k in set(source_files) & set(mirror_files) if source_files[k] != mirror_files[k])
    print(f"skill mirror: drift ({mirror})")
    for label, items in (("missing", missing), ("extra", extra), ("changed", changed)):
        if items:
            sample = ", ".join(items[:8])
            more = f", +{len(items) - 8} more" if len(items) > 8 else ""
            print(f"  {label}: {sample}{more}")
    return False


def _load_hooks(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def check_hooks(path: Path) -> bool:
    config = _load_hooks(path)
    hooks = config.get("hooks", {}) if isinstance(config, dict) else {}
    missing = []
    root = plugin_root()
    for event, matcher, name in install_codex_hooks.INSTALL_PLAN:
        expected_path = str(root / "hooks" / "codex" / name)
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
        if not found:
            missing.append(f"{event}/{name}")
    if missing:
        print(f"hooks: missing ({', '.join(missing)})")
        return False
    print(f"hooks: ok ({path})")
    return True


def check_gate_path() -> bool:
    common_path = plugin_root() / "hooks" / "codex" / "common.py"
    expected = plugin_root() / "skills" / SKILL_NAME / "scripts" / "forge_gate.py"
    spec = importlib.util.spec_from_file_location("falbe_hook_common_sync_check", common_path)
    if spec is None or spec.loader is None:
        print(f"gate path: missing common.py ({common_path})")
        return False
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    actual = Path(getattr(module, "GATE", ""))
    if actual.resolve() != expected.resolve():
        print(f"gate path: drift (actual {actual}, expected {expected})")
        return False
    print(f"gate path: ok ({expected})")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check installed Falbe Yeon Codex runtime sync.")
    parser.add_argument("--mirror", type=Path, default=default_mirror())
    parser.add_argument("--hooks-json", type=Path, default=install_codex_hooks.hooks_json_path())
    parser.add_argument("--skip-mirror", action="store_true")
    parser.add_argument("--skip-hooks", action="store_true")
    parser.add_argument("--skip-gate-path", action="store_true")
    args = parser.parse_args(argv)

    ok = True
    if not args.skip_mirror:
        ok = check_skill_mirror(args.mirror) and ok
    if not args.skip_hooks:
        ok = check_hooks(args.hooks_json) and ok
    if not args.skip_gate_path:
        ok = check_gate_path() and ok
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
