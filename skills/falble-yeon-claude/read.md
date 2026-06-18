# Falble Yeon Claude Hook Recovery Inventory

> Adapted and rebuilt distribution by ai.director_yeon. Thread ID: ai.director_yeon.

This file is the recovery index for the Claude adapter. If Fable/Mythos behavior
looks wrong later, use it to identify exactly which hooks belong to this package
and remove only those hooks.

## Package Identity

- Package folder: `falble-yeon-claude`
- Claude-facing skill: `skills/falble-yeon-claude`
- Shared core engine: `core/skills/falbe-yeon-codex/scripts`
- Lease identity used by the shared core: `falbe-yeon-codex`

## Hook Inventory

Installed Claude settings entries should point at these files inside the package
root:

- `hooks/user_prompt_submit.py`
  - Event: `UserPromptSubmit`
  - Handles explicit `fable gate on/off/status` and `mythos gate on/off/status`
    commands.
  - Does not auto-start ordinary prompts.

- `hooks/pre_tool_use.py`
  - Event: `PreToolUse`
  - Matcher: `Edit|Write|MultiEdit`
  - OFF, invalid lease, or no active task: pass through.
  - ON, valid lease, and active task: blocks implementation edits until SPEC
    passes.
  - `.forge/spec.json` edits are allowed.

- `hooks/post_tool_use.py`
  - Event: `PostToolUse`
  - Matcher: `Edit|Write|MultiEdit`
  - Records touched paths in `.forge/edits.txt` and `.forge/loop.json` only
    while ON with a valid lease and active task.

- `hooks/stop.py`
  - Event: `Stop`
  - Warns if the DONE gate is unmet while a gated task is active.

- `hooks/common.py`
  - Shared payload, path parsing, UTF-8, and core gate execution helpers.
  - Not registered directly as a hook.

## Install Checks

From the package root:

```powershell
python scripts\install_claude_hooks.py --dry-run
python scripts\install_claude_hooks.py --check
```

The installer checks both expected surfaces by default:

- hook entries in `~\.claude\settings.json`
- skill folder at `~\.claude\skills\falble-yeon-claude`

Use a custom settings file:

```powershell
python scripts\install_claude_hooks.py --settings-json C:\path\to\settings.json --check
```

Use a custom skills directory:

```powershell
python scripts\install_claude_hooks.py --skills-dir C:\path\to\skills --check
```

## Uninstall

```powershell
python scripts\install_claude_hooks.py --uninstall
```

Manual recovery: remove only hook entries whose command contains the absolute
path to this `falble-yeon-claude` package. The uninstaller leaves the copied
skill folder in place unless you remove it manually.

## Safety Rules

- Hook registration alone does not block edits.
- OFF, missing lease, expired lease, malformed lease, rebooted lease, or global
  disable means no edit blocking and no `loop.json` updates.
- Actual blocking begins only when the gate is ON, lease is valid, and
  `.forge/ACTIVE` exists.
- Run `off` after work is interrupted or finished.

## Local Verification

Automated simulated hook tests are maintained outside this share folder so the
published package stays clean. Live Claude Code hook firing should be verified
once in the target Claude environment.
