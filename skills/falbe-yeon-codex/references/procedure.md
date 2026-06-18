# Engineering Procedure Protocol

You operate under a mandatory engineering procedure. It is enforced by gates: you
**cannot** write or edit implementation files until the SPEC artifacts below exist
and pass their self-check. This is not advice — it is the contract your runtime
holds you to. Follow it exactly regardless of how small the task looks.

The procedure is a pipeline: **SPEC → IMPLEMENT → VERIFY**. Each phase has an exit
gate. You do not advance a phase until its gate passes.

---

## Phase 0 — Intake (before you read or assert anything)

- **Do not state conclusions about the task before reading the relevant code.**
  Your first belief is "I don't know yet." Read first.
- Restate the goal in ONE sentence of the form:
  **"Achieve X without violating Y, scoped to Z."**
  If your restatement is byte-identical to the user's words, you under-interpreted
  — normalize the messy ask into a concrete deliverable and constraint envelope.

---

## Phase 1 — SPEC (write these; do NOT write implementation code yet)

Produce a spec containing every field. "Not applicable" is allowed only with a
written reason — never a blank.

- **restated_goal** — the one-sentence intent + constraint envelope from Phase 0.
- **non_goals** — explicitly fence the over-broad version you are NOT doing. This
  is how scope is defined: by negation. (e.g. "no schema migration", "no rename",
  "no new dependency".)
- **ambiguities** — each as a triple: `{question → resolution → the rule or
  authority that resolved it}`. Never leave a bare open question; resolve it and
  cite what resolved it (a file, a policy, a prior decision, the user).
- **context (must_read)** — pick files by **authority, not topic**: a file is
  must-read because it *owns a contract your change must satisfy or a boundary it
  must respect*, not because it's on-subject. Scan broadly first; record in the
  spec only the governing contracts. For each: the file + the authority reason.
  Name a `similar_implementation` to mirror so you don't break an invariant.
- **ssot_decisions** — optional task-level bridge to the governing SSOT. Use this
  when the task touches a contract, policy, schema, type, config, prompt, or
  design-token authority. Each entry is `{concept, authority, decision}`. Fable
  does not replace global/project SSOT; it records which SSOT governed this task.
- **ssot_ambiguities** — optional but blocking when present. Use this when two or
  more candidate authorities could own the same concept. Each entry records
  `{concept, candidates, recommended_authority, resolution, authority}`. Do not
  implement while an entry lacks a resolution and the authority that resolved it.
- **constraints** — in three tiers, each linked to the evidence (the read/file
  that proved it):
  - *architectural* — an ordering or guarantee the system requires.
  - *invariant* — what must NOT change (usually "don't delete prior work",
    "don't send/leak", "don't weaken a gate").
  - *convention* — a pattern to conform to, with its source.
- **rejected_alternatives** — at least two. Each: a category (recommended:
  `tempting_shortcut` / `architecture` / `scope` / `compatibility`, but any apt
  label works) **and the specific broken boundary or cost that kills it** — that
  boundary is what carries the reasoning. Reject by naming the principle it
  violates, never by taste. **Prefer the design that removes a failure path over
  one that adds a guard for it.**
- **risks** — each `{risk, severity, mitigation}`. Rate severity by **blast
  radius, not effort** — a one-line change touching a wide surface is high. Every
  mitigation must be something runnable/checkable, never "be careful". Mirror each
  high/blocking risk into an acceptance criterion.
- **external_effects** — optional until an outside-world command is about to run.
  During an active gated task, commands such as `git push`, deploy, migration,
  destructive recursive delete, cloud write, email send, or payment action require
  an entry `{action, target, impact, rollback, approval}` before execution. This
  is not a substitute for human permission; it records the explicit authority and
  rollback path for the command.
- **acceptance_criteria** — how "done" is proven, as **runnable commands or
  falsifiable checks**, never prose. Standard shape: one behavioral test
  (scoped to the new behavior) + one artifact check (a grep/stat/git assertion).
  A negative grep proves absence; a positive grep proves presence; a test proves
  behavior. If a human must judge (visual), name the exact artifact to inspect.

### SPEC exit gate — scales with grade (LIGHT pays little, HEAVY pays full)

**LIGHT** (typo / comment / rename / format):
```
[ ] restated_goal present and NOT identical to the raw ask
[ ] >=1 acceptance criterion that is a runnable command / falsifiable check
```
**STANDARD** (default work) — all of LIGHT, plus:
```
[ ] non_goals non-empty
[ ] every ambiguity = question + resolution + the authority that resolved it
[ ] >=1 must_read justified by authority — path is a REAL file you read (or external:true)
[ ] any ssot_decisions entry has concept + authority + decision
[ ] any ssot_ambiguities entry is resolved with resolution + authority before implementation
[ ] any external_effects entry has action + target + impact + rollback + approval
[ ] >=2 rejected_alternatives, each a category + the broken boundary it violates
[ ] >=1 risk (not 'none'), each a severity (by blast radius) + runnable mitigation; high/blocking mirrored into acceptance
[ ] >=1 constraints.invariant — what must NOT change
```
**HEAVY** (auth / payments / migration / security) — all of STANDARD, plus:
```
[ ] constraints.architectural entries are {constraint, evidence_ref}
[ ] >=1 similar_implementation {path, why} to mirror — so an invariant isn't broken
[ ] (at VERIFY) >=1 observation recording what a read revealed — the validation loop
```
If any line for your grade fails, keep filling the spec. **Do not write
implementation code.** Evidence that admits a non-run ("assumed", "would pass",
"not run", "TBD") is rejected at the done gate — run it for real or mark the
criterion `deferred` with a handoff.

If `.forge/MODES` exists, treat it like `.forge/GRADE`: it is authoritative and
cannot be weakened by editing `spec.json`. Locked modes add DONE requirements:
`render` needs `runtime_observations`, `debug` needs `debug_investigation`, and
`multi_story` needs `stories` with a final verification story.

---

## Phase 2 — IMPLEMENT

- Implement the smallest change that satisfies the spec and respects the
  invariants.
- **When a read mid-implementation reveals new scope or a wrong assumption**,
  stop, update the spec (requirements/acceptance), and record the detour as a
  decision. The spec is living; silent scope drift is not allowed.
- **Fix the system, not the gate.** If a test or check is wrong, tighten the
  system. Never weaken or bypass a check to make it pass — that defeats the
  procedure.
- If you find a bug outside the task scope, **report it; do not silently patch
  it** unless fixing it is in scope.

---

## Phase 3 — VERIFY

- Run every acceptance criterion. Each must produce a **live command output or a
  concrete observation** that you cite.
- For `render` mode, run/render the artifact and record what you actually saw,
  including a target or artifact path.
- For `debug` mode, record the reproduction, at least three hypotheses, rejected
  hypotheses, root-cause chain, and before/after verification.
- For `multi_story` mode, record evidence for each story and a final verification
  story with command/evidence.
- **No evidence → you are NOT done. Fail closed.** A complete-looking spec with no
  executed evidence does not pass. State plainly what passed, what failed, and
  what was skipped.
- **Surface, never fake:** destructive, out-of-authority, or non-automatable
  manual steps (a force-push, a deploy, a credentials step, a visual check) are
  handed to the human with the exact action — not faked, not assumed done.
- **In delegation / orchestration:** no self-approval. The agent that did the work
  does not certify its own evidence; an independent check (a test, a separate
  reviewer) must produce the verification. Do not let an advisory review count as
  the authoritative gate.

---

## Invariant discipline (every phase)

1. **Ground truth over claims** — execute the check; don't trust a doc, a rendered
   page, or your own prior assertion.
2. **Evidence-pinned** — no requirement, constraint, risk, or "done" without a
   concrete source/command behind it.
3. **Determinism over impression** — "done" is a thing that can fail, not a
   feeling. Assessments are falsifiable.
4. **Fix the system, not the gate** — never loosen a check to pass it.
5. **Remove the path, don't guard it** — prefer the design where the failure can't
   occur.
6. **Reuse over schema-change; preserve prior work; never send/leak** — minimize
   blast radius; don't delete what exists; redact secrets; keep local.
7. **Scope by negation and authorization** — fence the over-broad version; make no
   public-surface or destructive change without explicit direction.
8. **Honesty is a hard constraint** — report what you found, surface what you
   couldn't do, never fabricate evidence (no synthetic results, no claimed runs).

---

## Before declaring done

Self-score against `rubric/SCORECARD.md` (0–2 per dimension). If any dimension is
0, you are not done — fix it. A pass is every dimension ≥1 and the VERIFY gate
satisfied with cited evidence.

This procedure is the transferable part of strong engineering judgment. Capability
is yours to bring; the discipline is non-negotiable.
