#!/usr/bin/env python3
"""Falbe Yeon Codex public facade and CLI entrypoint.

The engine is split by responsibility into:
- forge_state.py: state, lease, and loop persistence
- forge_validation.py: spec/done validation and evidence quality rules
- forge_commands.py: CLI command handlers

This module intentionally re-exports the historical API so existing hooks,
tests, and direct imports of forge_gate keep working.
"""
from __future__ import annotations

import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from forge_state import (  # noqa: E402,F401
    ACTIVE_NAME,
    DEFAULT_LEASE_TTL_SECONDS,
    FORGE_DIR,
    LEASE_NAME,
    LOOP_NAME,
    SCOPES,
    SPEC_NAME,
    _active_goal,
    _base_loop,
    _boot_marker,
    _bounded_events,
    _global_disable_path,
    _global_disabled,
    _iso_from_epoch,
    _lease_ttl,
    _load_loop,
    _machine_dir,
    _message_items,
    _now_epoch,
    _now_utc,
    _read_lease,
    _read_state,
    _safe_sid,
    _scope_states,
    _session_state_path,
    _write_lease,
    _write_loop,
    active_path,
    clear_lease,
    effective_state,
    issue_lease,
    lease_path,
    lease_status,
    load_spec,
    loop_path,
    record_loop_event,
    runtime_state,
    spec_path,
)
from forge_validation import (  # noqa: E402,F401
    ACC_TYPES,
    ALT_CATEGORIES,
    FAKE_MARKERS,
    HEAVY_KO,
    HEAVY_RE,
    NO_RISK_PLACEHOLDERS,
    QUESTION_KO_ENDINGS,
    SEVERITIES,
    SPEC_TEMPLATE,
    WEAK_EVIDENCE_EXACT,
    WORK_KO,
    WORK_RE,
    _effective_grade,
    _evidence_quality_errors,
    _forbidden_hits,
    _inv_text,
    _is_placeholder_risk,
    _nonempty,
    _norm,
    gate_done,
    gate_spec,
)
from forge_commands import (  # noqa: E402,F401
    LIGHT_KO,
    LIGHT_RE,
    _contract_text,
    _grade_for,
    cmd_active,
    cmd_classify,
    cmd_close,
    cmd_contract,
    cmd_lease,
    cmd_loop,
    cmd_runtime_state,
    cmd_scaffold,
    cmd_state,
    cmd_status,
    cmd_toggle,
    cmd_validate,
    main,
)

if __name__ == "__main__":
    raise SystemExit(main())
