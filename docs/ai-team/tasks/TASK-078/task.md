# TASK-078 — E-C Downstream Complete Design

- Status: `DESIGN_FROZEN / JUDGE_ACCEPTED / IMPLEMENTATION_EFFECTS_NOT_AUTHORIZED`
- Owner authority: explicit Owner-approved E-C downstream complete-design assignment
- Development profile: `DEV-4 FOUNDATION CRITICAL`
- Kickoff design base: `origin/main@74b85d7d3f5965cd515ff44bd5f4b7179185e578`
- Final integration base: `origin/main@354ea2534ad5739a099d9eeaf0f1da9a7210ddb6`
- Branch: `codex/task-078-ec-downstream-complete-design`
- Product: `BAI VIDEO PRODUCTION`

## Goal

Close the design from the current central-model and Planning surfaces through a
future public TASK-077 development-completion Gate and the canonical TASK-027
Scene-finalization receipt, AI Video Job, generated
video read-back and Human Review, generated-video-only Timeline placement,
Final Approval, Export Queue/result read-back and the packaged EXE F0-F10 flow.

TASK-078 is a design and integration-responsibility Task. It does not become a
second Scene, Asset, Audit, Timeline, Gate, Job or Export owner.

## Future implementation Task candidates

| Unit | Candidate identity | Integration owner | Canonical owners preserved |
|---|---|---|---|
| E-C1 Scene Epoch Downstream Binding | `TASK-079` | TASK-027 orchestration | TASK-027/013/037/036 only |
| E-C2 Generated Video Typed Read-back and Review | `TASK-080` | TASK-013/TASK-038 integration | TASK-013, TASK-003, TASK-027, TASK-037, TASK-038, TASK-036 |
| E-C4 Canonical Final Gate Owner Readers | `TASK-081` | each receipt owner | TASK-041, TASK-016, TASK-020, TASK-003 Rights, TASK-044; TASK-027 lineage supplier and TASK-036 consume-only |
| E-C3 Generated-video-only Timeline Placement | `TASK-082` | TASK-044 Timeline integration | TASK-003/037/038/043/044; TASK-036 Shell only |
| E-C5 Packaged Vertical Aggregate / EXE F0-F10 | `TASK-083` | TASK-036 Shell integration | every stage remains read through its canonical owner |

The numbering intentionally does not imply execution order. The dependency
order is `E-C1 -> {E-C2, E-C4} -> E-C3 -> E-C5`; E-C2 and E-C4 may execute in
parallel after E-C1.

## Authority and Human Gates

TASK-078 authorizes documentation, schema/ABI design and read-only inspection.
It grants zero authority for Provider or paid calls, native generation, media
probing, Timeline or Resolve writes, Final Approval, Export enqueue/dispatch,
Release, Deploy or Production Activation.

Future implementation candidates remain separately bounded. A design PASS or
PR merge does not authorize any prohibited effect.

## TASK-077 dependency rule

TASK-077 has an active private diff. TASK-078 does not read, compare, cherry-pick
or infer that diff. E-C1 may integrate only after TASK-077 publishes a canonical
public development-completion receipt on canonical main. This is an
implementation-start Gate and ABI provenance only; runtime Scene finalization,
epoch and invalidation remain TASK-027 authority. Until then, the dependency is
`TASK077_PUBLIC_COMPLETION_RECEIPT_NOT_CONFIRMED`, and downstream effect count is
zero.

Canonical main currently contains TASK-077's public design, which defines the
TASK-027 Proposal revision as structure-epoch owner and TASK-027 as GO/
finalization owner, but no public development-completion receipt. TASK-078
reads only that public design to align the handshake; it does not treat design
merge as completion or TASK-077 as Product Scene authority.

## Context scope

### MUST READ

- `AGENTS.md`
- `docs/ai-team/current-state.md`
- this Task and its E-C design files
- exact public TASK-027/013/037/038/036/043/044 contracts cited by the design
- exact target source types needed to verify ABI feasibility

### READ IF REQUIRED

- TASK-041 Audio Completion public contract evidence
- TASK-016 Privacy Guard public contract evidence
- TASK-020 Resource Admission public contract evidence
- TASK-003 Asset rights fields and TASK-011 Render QA contract

### DO NOT READ BY DEFAULT

- TASK-077 private worktree or diff
- unrelated active Task branches/worktrees
- archives, superseded roadmaps and full OS Architecture

### MAY MODIFY

- `docs/ai-team/tasks/TASK-078/**`
- `docs/ai-team/task-index.md`
- `docs/ai-team/current-state.md`
- `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md`
- one exact active-lock row only if required for PR integration

### MUST NOT MODIFY

- Product runtime source, tests or schemas
- TASK-077 files or branch
- BAI Development OS repository
- Provider, paid, native, Timeline, Export, Release, Deploy or Activation state

## Definition of done

- E-C1 through E-C5 each define identity, Owner, Allowed Files, prohibited
  effects, exact receipt ABI, UI transitions, restart/failure behavior, negative
  matrix and handoff.
- Existing responsibility is not overwritten and legacy/old Scene epochs have
  zero downstream effect.
- E-C2 and E-C4 remain independently implementable in parallel.
- Independent DEV-4 Critic and Judge report unresolved Critical/High `0 / 0`.
- static link/scope/diff checks pass.
- the completed design is delivered in one coherent design PR.

## Final design decision

- Completeness/Ownership Critic: `PASS`, residual Critical/High/Medium/Low
  `0 / 0 / 0 / 0`.
- Security/Integrity/Restart Critic: `PASS`, residual
  Critical/High/Medium/Low `0 / 0 / 0 / 0`.
- Independent Judge: `ACCEPT — TASK078_DESIGN_FROZEN`, residual
  Critical/High/Medium/Low `0 / 0 / 0 / 0`.
- TASK-079 through TASK-083 remain candidate implementation Tasks only. This
  decision allocates no implementation or runtime-effect authority.
- TASK-079 cannot start until a canonical public TASK-077
  development-completion receipt is confirmed on canonical main.
