---
name: falble-yeon-claude
description: "Use when the user explicitly asks for Fable, Mythos, an evidence gate, SPEC-before-implementation workflow, or hooks that enforce only while a gated task is active in Claude Code."
---

> Adapted and rebuilt distribution by ai.director_yeon. Thread ID: ai.director_yeon.

# Falble Yeon Claude

Claude Code adapter for the Falbe Yeon/Fable gate. The goal is the same gate
behavior level as the Codex package, adapted to Claude Code hook wiring.

## Runtime Model

The gate defaults to OFF. Hook registration alone must not block edits.

Actual enforcement requires all of these:

- project/session/machine state resolves to `on`
- `.forge/ACTIVE` exists
- `.forge/lease.json` exists and is valid
- lease root matches the current project
- lease has not expired
- lease boot marker matches the current boot session
- global disable is absent

If any check fails, hooks fail open.

## Start

From the project root, start a gated task through the packaged core:

```bash
python <package-root>/core/skills/falbe-yeon-codex/scripts/codex_fable_gate.py start --goal "<task>"
```

Then fill `.forge/spec.json`, validate SPEC, implement, record acceptance
evidence, validate DONE, and close.

## Hook Commands

The installed `UserPromptSubmit` hook handles explicit commands:

```text
fable gate on
fable gate status
fable gate off
mythos gate on
미토스 게이트 status
```

It does not auto-start ordinary prompts.

## Work Loop

1. Start the gate for a specific task.
2. Fill `.forge/spec.json` before implementation edits.
3. Run SPEC validation.
4. Implement only after SPEC passes.
5. Record live evidence for every acceptance criterion.
6. Validate DONE.
7. Close the task or run `off` if interrupted.

## Install / Check / Uninstall

From the package root:

```bash
python scripts/install_claude_hooks.py --dry-run
python scripts/install_claude_hooks.py
python scripts/install_claude_hooks.py --check
python scripts/install_claude_hooks.py --uninstall
```

The default install registers hooks and copies this skill to
`~/.claude/skills/falble-yeon-claude`. Use `--settings-json <path>` to target a
specific Claude settings file, `--skills-dir <path>` to target a specific skills
directory, or `--hooks-only` only when the skill folder is already installed.

## Recovery

Disable a project gate from the project root:

```bash
python <package-root>/core/skills/falbe-yeon-codex/scripts/codex_fable_gate.py off
```

If hook wiring itself is wrong, run:

```bash
python scripts/install_claude_hooks.py --uninstall
```

Manual recovery: remove only hook entries whose command path points into this
`falble-yeon-claude` package.

## Verification Boundary

The included tests simulate Claude hook payloads locally. Treat the package as
Claude-ready after local tests pass, then verify hook firing once inside the live
Claude Code environment before calling it a stable runtime release.
