---
name: falbe-yeon-codex
description: "Use when the user explicitly says 페이블, 미토스, Fable, Mythos, FableCodex, asks for a Falbe Yeon gate/hook, wants hooks active only while the skill is used, wants SPEC to IMPLEMENT to VERIFY blocking, or asks for .forge/spec.json evidence-gated work."
---

# Falbe Yeon Codex

## Purpose

Use this skill when a task should be protected by a hard Codex gate. The gate is off by default. This skill turns it on for the current project, creates `.forge/spec.json`, blocks implementation edits until the SPEC gate passes, and turns it off after DONE passes.

This is Codex-only. Do not use non-Codex adapters, status lines, or host settings. Preserve active Codex system, developer, sandbox, approval, and tool instructions.

Read `read.md` in this skill folder for the installed hook inventory, skill inventory, and recovery/off/uninstall commands.

The installed hooks may remain registered, but enforcement requires a fresh project lease. No valid `.forge/lease.json` means hooks fail open and do not block or record. A lease expires automatically after the TTL, is rejected after reboot, and is cleared by `off` or `close`.

## Activation Philosophy

The user can invoke this workflow with short trigger words such as `페이블`,
`미토스`, `Fable`, `Mythos`, or `FableCodex`. The goal is to make deliberate
gated work easy to request without making every ordinary Codex task heavy.

This skill is intentionally opt-in. Lightweight questions, quick file checks,
and small low-risk edits do not need a full SPEC-to-IMPLEMENT-to-VERIFY loop,
and forcing that loop on every turn wastes context and usage. Fable is the
switch for work that deserves stronger evidence, not a permanent tax on every
conversation.

Hook registration is therefore separate from hook enforcement. Hooks may remain
installed, but they only enforce when the project gate is ON, an active task
exists, and a valid lease exists. When the task closes, `off` is called, the
lease expires, or the machine reboots, enforcement falls open so stale sessions
do not keep blocking normal work.

## Local State Files

- `.forge/spec.json`: task contract, task-level SSOT decisions/ambiguities, external-effect approvals, and acceptance evidence SSOT.
- `.forge/loop.json`: local Fable loop state for phase, last failure, next action, and edited paths.
- `.forge/edits.txt`: append-only touched-file ledger used by the done gate.
- `.forge/lease.json`: short-lived runtime permission for hooks to enforce this skill.
- `.forge/MODES`: locked task modes detected at start. Supported modes are `render`, `debug`, and `multi_story`; this file is authoritative even if `spec.json` is edited later.

Hooks must read or write `.forge/loop.json` only after the gate is ON, a valid lease exists, and an active task exists. Do not paste the whole loop file into chat; use `status` for the short summary.

## Start

1. Resolve this skill directory.
2. Run:

```bash
python <skill-dir>/scripts/codex_fable_gate.py start --goal "<user task>"
```

3. Read the printed gate contract.
4. Fill `.forge/spec.json` completely before editing implementation files.
5. Validate before edits:

```bash
python <skill-dir>/scripts/codex_fable_gate.py validate-spec
```

If validation fails, edit only `.forge/spec.json` until it passes.

For long gated work, renew the lease before implementation edits:

```bash
python <skill-dir>/scripts/codex_fable_gate.py heartbeat
```

## Work Loop

- Inspect SSOT and governing files before conclusions.
- Do not copy global/project SSOT rules into Fable. Cite the governing authority in `ssot_decisions`; if authorities conflict, record it in `ssot_ambiguities` and resolve it before implementation.
- Before push/deploy/migration/destructive delete/cloud write/email/payment commands during an active gated task, record `external_effects` with action, target, impact, rollback, and approval.
- Keep scope narrow: state non-goals and forbidden paths.
- Use `.forge/spec.json` as the task contract.
- Use `.forge/loop.json` as the local state board; keep it out of chat unless a short status is needed.
- Do not edit implementation files until `validate-spec` passes.
- If new scope appears, update `.forge/spec.json` first.
- Run real checks from `acceptance_criteria`; do not fabricate evidence.
- If the printed contract mentions locked modes, satisfy their DONE evidence:
  - `render`: add `runtime_observations` from a real renderer/run with target or artifact.
  - `debug`: add `debug_investigation` with reproduction, 3 hypotheses, rejected hypotheses, root-cause chain, and before/after verification.
  - `multi_story`: add `stories` with evidence per story and a final verification story.

For the full field contract, read `references/procedure.md`. For scoring and review, read `references/scorecard.md`.

## Finish

1. Run every acceptance command/check.
2. Write live output into each acceptance criterion's `evidence`.
3. Validate done:

```bash
python <skill-dir>/scripts/codex_fable_gate.py validate-done
```

4. Close and turn the project gate off:

```bash
python <skill-dir>/scripts/codex_fable_gate.py close
```

If work is interrupted or the user asks to stop, run:

```bash
python <skill-dir>/scripts/codex_fable_gate.py off
```

If the process or computer stops before this can run, the lease expires and hooks fail open on the next run.

## Hook Install

The skill can guide gated work only after hooks are installed. Install or refresh Codex hooks from the plugin root:

```bash
python scripts/install_codex_hooks.py
```

This merges with existing hooks and keeps the gate off by default. To remove only these hooks:

```bash
python scripts/install_codex_hooks.py --uninstall
```

## Commands

- `python <skill-dir>/scripts/codex_fable_gate.py status`
- `python <skill-dir>/scripts/codex_fable_gate.py heartbeat`
- `python <skill-dir>/scripts/codex_fable_gate.py off`
- `python <skill-dir>/scripts/forge_gate.py validate --root . --gate spec`
- `python <skill-dir>/scripts/forge_gate.py validate --root . --gate done`
- `python <skill-dir>/scripts/forge_gate.py external-effect --root . --command "<shell command>"`
