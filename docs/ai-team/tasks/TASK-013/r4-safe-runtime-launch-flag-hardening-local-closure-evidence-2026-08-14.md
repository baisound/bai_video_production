# TASK-013 — R4 Safe Runtime Launch-Flag Hardening Local Closure Evidence

- Date: `2026-08-14`
- Branch: `codex/task-013-safe-runtime-hardening`
- Base main: `21228d15e207fb76c5367c28968430789f682885`
- BAI Development OS queue selection: `TASK-013-SAFE-RUNTIME-HARDENING / IMPLEMENTATION`
- Local gate: `PASS`
- Native H3 gate: `PARKED_TO_SAFE_RUNTIME_REVIEW`

## Implemented bounded unit

The exact local Comfy adapter now rejects every memory-related launch flag
observed in the Owner-confirmed force-restart attempt:

- `--disable-dynamic-vram`;
- `--disable-async-offload`;
- `--disable-pinned-memory`;
- `--lowvram`.

The existing `--cpu`, `--gpu-only`, `--highvram` and `--novram` exclusions are
retained. Both exact tokens and assignment-form arguments are rejected. The
runtime check remains before dispatch-journal reservation and before the Comfy
queue call, so rejection creates no false durable execution state and performs
no Provider side effect.

## Implementation Critic

- the prior uncertain `QUEUED / RECOVERY_REQUIRED` execution is not read,
  rewritten or replayed;
- no third native attempt is enabled or authorized;
- original offending argument text remains visible in structured error details;
- no route, Prompt, workflow, model, output or Candidate/Audit behavior changes;
- unresolved implementation Critical/High findings: `0 / 0`.

## Validation

- focused adapter/controller/launcher regression: `39 / 39 PASS`;
- full WSL2 Ubuntu regression: `923 / 923 PASS`;
- WSL2 `compileall`: PASS;
- `git diff --check`: PASS before publication;
- no native generation, paid Provider, Resolve/Cubase mutation, Tag, Release or
  Production operation occurred;
- pre-existing untracked `evidence/native/**` remains outside the change.

## Claim boundary

This closes only the repository-level incident flag hardening. It does not prove
host/GPU stability, native H3 completion, generated-media quality, Candidate or
TASK-040 Attempt binding, TASK-013 overall completion or R4 overall completion.
The exact Native Gate remains parked and still requires a separately reviewed
safe-runtime strategy and fresh preflight before any future execution.

Hosted integration is determined by the Pull Request containing this record.
Stable release remains `v0.20.1`; this bounded corrective unit selects no new
package version, Tag or GitHub Release.
