# Falbe Yeon Codex Hook Recovery Inventory

This file exists as the recovery index for this skill. If Fable/Mythos behavior looks wrong later, use this file to identify exactly which hooks belong to `falbe-yeon-codex` and remove only those hooks.

이 파일의 목적은 사용법 안내가 아니라 복구용 식별표입니다. 문제가 생기면 이 스킬과 연결된 훅만 빠르게 찾아 끊기 위해 둡니다.

## Trigger Words

Use this skill for:

- `페이블`
- `미토스`
- `Fable`
- `Mythos`
- `FableCodex`
- `falbe-yeon-codex`

The gate still defaults to OFF. Triggering the skill does not mean implementation edits are blocked until the skill start command creates an active task.

Runtime enforcement also requires a fresh `.forge/lease.json`. If the lease is missing, expired, malformed, or from a previous boot session, registered hooks fail open and do not block edits. This is intentional fail-open lease behavior.

## Skill

- `falbe-yeon-codex`
  - Frontmatter trigger and workflow instructions live in `SKILL.md`.
  - Hook/recovery SSOT lives in this file: `read.md`.
  - `README.md` is only a discoverability pointer back to `read.md`.
  - Main wrapper: `scripts/codex_fable_gate.py`
  - Gate facade / CLI compatibility entrypoint: `scripts/forge_gate.py`
  - Gate state / lease SSOT: `scripts/forge_state.py`
  - Gate validation / evidence SSOT: `scripts/forge_validation.py`
  - Gate command handlers: `scripts/forge_commands.py`
  - Mode gate SSOT: `scripts/forge_modes.py`
  - Optional semantic judge: `scripts/forge_judge.py`
  - Contract references: `references/procedure.md`, `references/scorecard.md`

Expected installed locations after local install:

- Skill: `%USERPROFILE%\.agents\skills\falbe-yeon-codex`
- Stable plugin package: `<plugin-root>`
- Optional development/source package, if present: `<source-checkout>\falbe-yeon-codex`

Runtime authority is the stable plugin package. The skill directory under
`.agents\skills\falbe-yeon-codex` is the discoverability mirror used by Codex
skill loading. Do not treat an optional Desktop/source checkout as runtime
authority unless it is explicitly installed or synced into the stable plugin
package.

## Runtime Sync Check

Use this check when hook or SSOT behavior looks inconsistent:

```powershell
python <plugin-root>\scripts\check_sync.py
```

It verifies:

- the stable plugin skill and `.agents\skills\falbe-yeon-codex` mirror match
- `hooks.json` contains the expected four hook registrations for this plugin
- `hooks\common.py` points to the bundled plugin gate engine

## Hooks

These hook scripts are part of the plugin package. They are only effective after `scripts/install_codex_hooks.py` registers them in Codex hooks.

Non-mutating hook checks from the plugin root:

```powershell
python scripts\install_codex_hooks.py --dry-run
python scripts\install_codex_hooks.py --check
```

Direct installed commands:

```powershell
python <plugin-root>\scripts\install_codex_hooks.py --dry-run
python <plugin-root>\scripts\install_codex_hooks.py --check
```

Registered Codex hook file:

```text
%USERPROFILE%\.codex\hooks.json
```

Backup made before this package installed hooks:

```text
%USERPROFILE%\.codex\hooks.json.codex-fable-backup-YYYYMMDD-HHMMSS.bak
```

Installed hook command root:

```text
<plugin-root>\hooks
```

Any hook entry whose `command` contains `falbe-yeon-codex` belongs to this skill/plugin.

- `hooks/user_prompt_submit.py`
  - Handles explicit gate commands.
  - Registered event: `UserPromptSubmit`
  - Installed command:
    `"python" "<plugin-root>\hooks\user_prompt_submit.py"`
  - Commands include `fable gate on/off/status`, `mythos gate on/off/status`, `페이블 게이트 on/off/status`, `미토스 게이트 on/off/status`.
  - Does not auto-start ordinary prompts.

- `hooks/pre_tool_use.py`
  - Registered event: `PreToolUse`
  - Registered matcher: `apply_patch|Edit|Write|shell_command|functions\.shell_command|Bash|bash|Shell`
  - Installed command:
    `"python" "<plugin-root>\hooks\pre_tool_use.py"`
  - OFF, invalid lease, or no active task: pass through.
  - ON, valid lease, and active: blocks implementation edits until the SPEC gate passes.
  - `.forge/spec.json` edits are allowed.
  - Shell commands pass through unless they clearly create an external effect. During an active gated task, `git push`, deploy, migration, destructive recursive delete, cloud write, email send, or payment actions require `.forge/spec.json` `external_effects` approval.

- `hooks/post_tool_use.py`
  - Registered event: `PostToolUse`
  - Registered matcher: `apply_patch|Edit|Write`
  - Installed command:
    `"python" "<plugin-root>\hooks\post_tool_use.py"`
  - OFF, invalid lease, or no active task: pass through.
  - ON, valid lease, and active: records touched paths in `.forge/edits.txt` and `.forge/loop.json`.

- `hooks/stop.py`
  - Registered event: `Stop`
  - Installed command:
    `"python" "<plugin-root>\hooks\stop.py"`
  - OFF, invalid lease, or no active task: pass through.
  - ON, valid lease, and active: warns if the DONE gate is unmet.

- `hooks/common.py`
  - Shared Codex payload, UTF-8, path parsing, and gate state helpers.
  - Not registered directly as a hook.

This package did not add `PermissionRequest` or `SessionStart` hooks.

## Local State Files

Inside each gated project:

- `.forge/STATE`: project gate state, `on` or `off`.
- `.forge/lease.json`: short-lived runtime lease. Hooks enforce only while this file is valid.
- `.forge/ACTIVE`: active gated task marker.
- `.forge/MODES`: locked task-mode marker, one mode per line. Supported values are `render`, `debug`, `multi_story`.
- `.forge/spec.json`: task contract and evidence SSOT.
  - `external_effects` records approval, impact, target, and rollback for outside-world commands.
- `.forge/loop.json`: local phase, last failure, next action, and edited paths.
- `.forge/edits.txt`: touched-file ledger for done-gate checks.

Machine-level state, only if used:

- `%USERPROFILE%\.config\forge\STATE`
- Or `%FORGE_HOME%\STATE` if `FORGE_HOME` is set.

Global emergency kill switch:

- `%USERPROFILE%\.codex\fable-disable`
- Or environment variable `FORGE_DISABLE=1`

If either exists, Fable hooks fail open even when project state and lease are on.

## Lease / Crash Safety

The hook files can remain registered in `hooks.json`, but they do not enforce from registration alone.

Runtime enforcement requires all of these to be true:

- raw state resolves to `on`
- `.forge/lease.json` exists and has `status: on`
- lease root matches the current project root
- lease has not expired
- lease boot marker matches the current boot session
- global kill switch is absent
- `.forge/ACTIVE` exists

If any check fails, hooks return success and do not block edits or update `loop.json`.

Mode gates do not change hook activation. They only add DONE-gate requirements after the project is already ON with a valid lease and active task.

Mode evidence fields in `.forge/spec.json`:

- `runtime_observations`: required by `render` mode. Record the real run/render target or artifact and what was observed.
- `debug_investigation`: required by `debug` mode. Record reproduction, at least three hypotheses, rejected hypotheses, root-cause chain, and before/after verification.
- `stories`: required by `multi_story` mode. Record each story's status/evidence and a final verification story.

This is the crash-safe behavior: if Codex, Python, or the PC shuts down before cleanup runs, heartbeat stops and the lease expires. After reboot, the boot marker also invalidates the old lease.

Default lease TTL:

```text
300 seconds
```

Override for testing only:

```powershell
$env:FORGE_LEASE_TTL_SECONDS="30"
```

## Turn Gate Off

From the project root:

```powershell
python <skill-dir>\scripts\codex_fable_gate.py off
```

Or type one of these in Codex:

```text
fable gate off
mythos gate off
페이블 게이트 off
미토스 게이트 off
```

If needed, inspect status:

```powershell
python <skill-dir>\scripts\codex_fable_gate.py status
python <skill-dir>\scripts\codex_fable_gate.py runtime-state
```

Renew a live gated task before long implementation edits:

```powershell
python <skill-dir>\scripts\codex_fable_gate.py heartbeat
```

## Uninstall Hooks

From the plugin root:

```powershell
python scripts\install_codex_hooks.py --check
python scripts\install_codex_hooks.py --uninstall
```

This removes only hook entries whose command path points to this plugin package.

Direct installed command:

```powershell
python <plugin-root>\scripts\install_codex_hooks.py --check
python <plugin-root>\scripts\install_codex_hooks.py --uninstall
```

If manual recovery is needed, open:

```text
%USERPROFILE%\.codex\hooks.json
```

Then remove only hook entries whose `command` contains one of these:

```text
falbe-yeon-codex
<plugin-root>
```

Do not remove unrelated hooks from other plugins or user workflows.

If a bad mode lock is the problem but hooks themselves are healthy, remove or edit only the project-local file:

```text
<project>\.forge\MODES
```

Removing `.forge/MODES` disables mode-specific DONE requirements for that project, but does not uninstall hooks.

Emergency restore option:

```powershell
Copy-Item -LiteralPath "%USERPROFILE%\.codex\hooks.json.codex-fable-backup-YYYYMMDD-HHMMSS.bak" -Destination "%USERPROFILE%\.codex\hooks.json" -Force
```

After removing hooks, verify there is no `falbe-yeon-codex` command left in:

```text
%USERPROFILE%\.codex\hooks.json
```

## Safety Rules

- The hook files may remain registered, but the gate defaults to OFF.
- OFF, missing lease, expired lease, malformed lease, rebooted lease, or global disable means no edit blocking and no `loop.json` updates.
- `fable gate on` turns state on, but implementation edits still pass until a skill `start` creates `.forge/ACTIVE`.
- Actual blocking begins only when the gate is ON, lease is valid, and `.forge/ACTIVE` exists.
- Mode-specific checks are DONE-gate checks only; they do not make hooks active without a lease.
- Run `off` after work is interrupted or finished.
