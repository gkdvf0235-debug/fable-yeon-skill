# Fable Yeon Skill

> Packaged by `ai._.yeon` / `ai.director_yeon`

## 한국어 소개

Fable Yeon Skill은 Codex와 Claude Code에서 함께 사용할 수 있는 **검증 게이트 스킬 패키지**입니다.

이 패키지는 작업을 바로 수정부터 시작하지 않고, 먼저 `.forge/spec.json`에 목표, 범위, 검증 기준을 적게 만든 뒤 구현을 진행하도록 돕습니다. 게이트가 켜져 있을 때는 SPEC 검증이 통과하기 전까지 구현 파일 수정을 막고, 작업이 끝날 때는 실제 실행 결과를 근거로 DONE 검증을 요구합니다.

쉽게 말하면, 중요한 작업을 할 때 AI가 “대충 했습니다”라고 말하지 못하게 하고, **계획 -> 구현 -> 실제 검증** 흐름을 강제로 지키게 만드는 안전장치입니다.

## English Overview

Fable Yeon Skill is a **verification gate skill package** for both Codex and Claude Code.

Instead of letting an agent jump directly into implementation, this package asks it to define the goal, scope, and acceptance checks in `.forge/spec.json` first. When the gate is active, implementation edits are blocked until the SPEC check passes. At the end, DONE validation requires real evidence from actual commands or artifacts.

In short, it helps prevent vague “done” claims and pushes the workflow into a clear **plan -> implement -> verify** loop.

## 지원 환경 / Supported Runtimes

- Codex
- Claude Code

Both adapters are included in this one folder.

이 폴더 하나에 Codex용과 Claude Code용 파일이 모두 들어 있습니다.

## 폴더 구조 / Folder Layout

- `skills/falbe-yeon-codex/`
  - Codex용 스킬과 게이트 엔진
  - Codex-facing skill and gate engine
- `skills/falble-yeon-claude/`
  - Claude Code용 스킬 설명
  - Claude Code-facing skill instructions
- `hooks/codex/`
  - Codex hook adapter scripts
- `hooks/claude/`
  - Claude Code hook adapter scripts
- `scripts/install_codex_hooks.py`
  - Codex hook installer/checker
- `scripts/install_claude_hooks.py`
  - Claude Code hook and skill installer/checker
- `core/skills/falbe-yeon-codex/scripts/`
  - Claude adapter가 사용하는 공유 게이트 엔진 미러
  - Shared gate engine mirror used by the Claude adapter
- `examples/hooks.json`
  - Codex hook example
- `examples/claude-settings.example.json`
  - Claude Code hook example

## 중요한 동작 방식 / Important Behavior

한국어:

- hook을 설치해도 바로 모든 작업을 막지는 않습니다.
- 게이트는 기본적으로 OFF입니다.
- 실제 차단은 활성 작업과 유효한 `.forge/lease.json`이 있을 때만 동작합니다.
- 작업이 중단되거나 lease가 만료되면 fail-open 방식으로 일반 작업을 방해하지 않습니다.

English:

- Installing hooks does not immediately block all work.
- The gate is OFF by default.
- Enforcement only starts when there is an active gated task and a valid `.forge/lease.json`.
- If the task is interrupted or the lease expires, the hooks fail open so normal work is not blocked.

## Codex 설치 / Codex Install

Run from this folder:

```powershell
python scripts\install_codex_hooks.py --dry-run
python scripts\install_codex_hooks.py
python scripts\install_codex_hooks.py --check
```

Codex hook만 제거하려면:

To remove only these Codex hooks:

```powershell
python scripts\install_codex_hooks.py --uninstall
```

## Claude Code 설치 / Claude Code Install

Run from this folder:

```powershell
python scripts\install_claude_hooks.py --dry-run
python scripts\install_claude_hooks.py
python scripts\install_claude_hooks.py --check
```

한국어:

Claude installer는 `~\.claude\settings.json`에 hook을 등록하고, Claude용 스킬을 `~\.claude\skills\falble-yeon-claude`로 복사합니다.

English:

The Claude installer registers hooks in `~\.claude\settings.json` and copies the Claude-facing skill to `~\.claude\skills\falble-yeon-claude`.

Custom paths:

```powershell
python scripts\install_claude_hooks.py --settings-json <path>
python scripts\install_claude_hooks.py --skills-dir <path>
```

Claude hook만 제거하려면:

To remove only these Claude hooks:

```powershell
python scripts\install_claude_hooks.py --uninstall
```

## 사용 흐름 / Workflow

한국어:

1. 게이트를 사용할 작업에서 Fable/Falbe/미토스 스킬을 호출합니다.
2. `.forge/spec.json`에 작업 목표와 검증 조건을 적습니다.
3. SPEC 검증을 통과한 뒤 구현합니다.
4. 실제 명령 실행 결과나 산출물로 DONE 증거를 채웁니다.
5. DONE 검증을 통과한 뒤 gate를 닫습니다.

English:

1. Invoke the Fable/Falbe/Mythos skill for a task.
2. Fill `.forge/spec.json` with the goal and acceptance checks.
3. Implement only after SPEC validation passes.
4. Record real command output or artifact evidence for DONE.
5. Close the gate after DONE validation passes.

## Codex Runtime Commands

```powershell
python skills\falbe-yeon-codex\scripts\codex_fable_gate.py status
python skills\falbe-yeon-codex\scripts\codex_fable_gate.py start --goal "<task>"
python skills\falbe-yeon-codex\scripts\codex_fable_gate.py validate-spec
python skills\falbe-yeon-codex\scripts\codex_fable_gate.py validate-done
python skills\falbe-yeon-codex\scripts\codex_fable_gate.py close
```

Claude Code uses the same gate engine through:

```powershell
python core\skills\falbe-yeon-codex\scripts\codex_fable_gate.py status
```

## 검증 / Verification

이 공개 배포본에는 내부 개발용 pytest 테스트 파일을 포함하지 않습니다.

This public distribution does not include the internal development pytest suite.

기본 설치 검증:

Basic package checks:

```powershell
python scripts\install_codex_hooks.py --dry-run
python scripts\install_claude_hooks.py --dry-run
python skills\falbe-yeon-codex\scripts\codex_fable_gate.py status
```

Claude Code adapter는 실제 Claude Code 환경에서 hook이 발화하는지 한 번 더 확인하는 것을 권장합니다.

For the Claude Code adapter, verify hook firing once inside a real Claude Code environment before calling it a stable live runtime release.

## Credit / Notice

Packaged by `ai._.yeon` / `ai.director_yeon`.

This is an adapted and rebuilt distribution. It is not a claim of original authorship from scratch. Preserve applicable upstream license and credit notices when publishing or redistributing.
