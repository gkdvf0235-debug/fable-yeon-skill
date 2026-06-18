"""Codex-native Yeon/Fable task modes.

This module is deliberately deterministic and local-only. It keeps task-mode
requirements inside `.forge` gates without host-specific hooks, external state,
setup scripts, or always-on routing.
"""
from __future__ import annotations

import re
from pathlib import Path

SUPPORTED_MODES = ("render", "debug", "multi_story")
MODES_NAME = "MODES"

RENDER_RE = re.compile(r"\b(html|svg|game|canvas|chart|render|website|webpage|ui|browser)\b", re.I)
DEBUG_RE = re.compile(r"\b(debug|bug|error|traceback|stack trace|crash|failing|not working|root cause)\b", re.I)
MULTI_RE = re.compile(r"\b(multi[- ]?step|multi[- ]?story|story|stories|refactor|migration|migrate|pipeline)\b", re.I)

RENDER_KO = ("게임", "브라우저", "렌더", "차트", "캔버스", "웹", "화면", "UI")
DEBUG_KO = ("디버그", "버그", "오류", "에러", "크래시", "안됨", "안되", "원인")
MULTI_KO = ("여러", "전체", "단계", "스토리", "리팩", "마이그", "파이프라인")


def _nonempty(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def classify_modes(goal: str) -> list[str]:
    text = goal or ""
    modes: list[str] = []
    if RENDER_RE.search(text) or any(k in text for k in RENDER_KO):
        modes.append("render")
    if DEBUG_RE.search(text) or any(k in text for k in DEBUG_KO):
        modes.append("debug")
    if MULTI_RE.search(text) or any(k in text for k in MULTI_KO):
        modes.append("multi_story")
    return modes


def modes_path(root: Path, forge_dir: str) -> Path:
    return Path(root) / forge_dir / MODES_NAME


def write_locked_modes(root: Path, forge_dir: str, modes: list[str]) -> None:
    clean = [m for m in modes if m in SUPPORTED_MODES]
    if not clean:
        return
    path = modes_path(root, forge_dir)
    if not path.exists():
        path.write_text("\n".join(clean) + "\n", encoding="utf-8")


def locked_modes(root: Path | None, forge_dir: str, spec: dict | None = None) -> list[str]:
    out: list[str] = []
    if root is not None:
        path = modes_path(Path(root), forge_dir)
        if path.exists():
            try:
                out = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()]
            except Exception:
                out = []
    if not out and isinstance(spec, dict):
        raw = spec.get("task_modes") or []
        if isinstance(raw, str):
            raw = [raw]
        if isinstance(raw, list):
            out = [str(m).strip() for m in raw]
    seen = set()
    clean = []
    for mode in out:
        if mode in SUPPORTED_MODES and mode not in seen:
            clean.append(mode)
            seen.add(mode)
    return clean


def gate_spec(spec: dict, root: Path | None, forge_dir: str) -> list[str]:
    # Mode requirements are mostly DONE-time because render/debug/story evidence
    # is produced during implementation. Keep SPEC permissive to avoid paperwork.
    return []


def _render_errors(spec: dict, root: Path | None) -> list[str]:
    observations = spec.get("runtime_observations") or []
    if not isinstance(observations, list) or not observations:
        return ["render mode requires runtime_observations with actual run/render observations before DONE."]
    errors = []
    good = False
    for i, obs in enumerate(observations):
        if not isinstance(obs, dict):
            errors.append(f"render mode runtime_observations[{i}] must be an object.")
            continue
        observation = obs.get("observation")
        target = obs.get("target")
        artifact = obs.get("artifact")
        if not _nonempty(observation):
            errors.append(f"render mode runtime_observations[{i}].observation is empty.")
            continue
        if not (_nonempty(target) or _nonempty(artifact)):
            errors.append(f"render mode runtime_observations[{i}] needs target or artifact.")
            continue
        if _nonempty(artifact) and root is not None and not (Path(root) / artifact).exists():
            errors.append(f"render mode runtime_observations[{i}].artifact '{artifact}' not found under root.")
            continue
        good = True
    if not good and not errors:
        errors.append("render mode requires at least one concrete runtime_observations entry.")
    return errors


def _debug_errors(spec: dict) -> list[str]:
    inv = spec.get("debug_investigation") or {}
    if not isinstance(inv, dict) or not inv:
        return ["debug mode requires debug_investigation before DONE."]
    errors = []
    repro = inv.get("reproduction") or {}
    if not (isinstance(repro, dict) and _nonempty(repro.get("command")) and _nonempty(repro.get("evidence"))):
        errors.append("debug mode requires reproduction.command and reproduction.evidence.")
    hypotheses = inv.get("hypotheses") or []
    good_h = [h for h in hypotheses if isinstance(h, dict) and _nonempty(h.get("hypothesis")) and _nonempty(h.get("evidence"))]
    if len(good_h) < 3:
        errors.append("debug mode requires at least 3 hypotheses with evidence.")
    rejected = inv.get("rejected_hypotheses") or []
    good_r = [h for h in rejected if isinstance(h, dict) and _nonempty(h.get("hypothesis")) and _nonempty(h.get("evidence"))]
    if not good_r:
        errors.append("debug mode requires rejected_hypotheses with evidence.")
    if not _nonempty(inv.get("root_cause_chain")):
        errors.append("debug mode requires root_cause_chain.")
    before_after = inv.get("before_after_verification") or {}
    if not (isinstance(before_after, dict) and _nonempty(before_after.get("before")) and _nonempty(before_after.get("after"))):
        errors.append("debug mode requires before_after_verification.before and after.")
    return errors


def _story_errors(spec: dict) -> list[str]:
    stories = spec.get("stories") or []
    if not isinstance(stories, list) or len(stories) < 2:
        return ["multi_story mode requires stories with at least one work story and a final verification story."]
    errors = []
    for i, story in enumerate(stories):
        if not isinstance(story, dict):
            errors.append(f"multi_story mode stories[{i}] must be an object.")
            continue
        if story.get("status") != "complete":
            errors.append(f"multi_story mode stories[{i}] is not complete.")
        if not _nonempty(story.get("evidence")):
            errors.append(f"multi_story mode stories[{i}] needs evidence.")
    final = stories[-1] if isinstance(stories[-1], dict) else {}
    verification = final.get("verification") or {}
    if not (isinstance(verification, dict) and _nonempty(verification.get("command")) and _nonempty(verification.get("evidence"))):
        errors.append("multi_story mode requires final verification story with verification.command and verification.evidence.")
    return errors


def gate_done(spec: dict, root: Path | None, forge_dir: str) -> list[str]:
    modes = locked_modes(root, forge_dir, spec)
    errors: list[str] = []
    if "render" in modes:
        errors.extend(_render_errors(spec, root))
    if "debug" in modes:
        errors.extend(_debug_errors(spec))
    if "multi_story" in modes:
        errors.extend(_story_errors(spec))
    return errors


def contract_text() -> str:
    return (
        "Mode lock: start may write .forge/MODES (render/debug/multi_story). "
        "These modes are authoritative even if task_modes is removed from spec.json. "
        "At DONE: render mode requires runtime_observations with observed target/artifact; "
        "debug mode requires debug_investigation with reproduction, 3 hypotheses, rejected_hypotheses, "
        "root_cause_chain, and before_after_verification; multi_story mode requires stories with "
        "evidence and a final verification story."
    )
