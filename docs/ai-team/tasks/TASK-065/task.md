# TASK-065 — Production Montage Learning Linkage Closure

- Status: `ALLOCATED / PRE_IMPLEMENTATION_DEPENDENCY_GATED`
- Capability: `BVP-PRODUCTION-MONTAGE-LEARNING-LINKAGE-001`
- Development profile: `DEV-4 FOUNDATION CRITICAL`
- Canonical audit base: `160c9569673fbf65a28b0f95eeb44c5b0111584f`
- Owner request: establish the production SKILL-to-BVP linkage under the canonical rules without interrupting or reassigning the three active development lanes.

## Objective

Consume, without taking ownership from them:

- TASK-058 released SKILL interchange and Bridge transport;
- TASK-060 PP-C exact promoted advisory Preference source;
- TASK-061 CA-C Human activation/deactivation and config history;
- TASK-063 installer-selected-root-relative instance and discovery evidence.

TASK-065 closes production coordinate synchronization and real read-back/E2E.
It does not reimplement Timeline/Resolve ownership, learning admission,
Preference promotion, or connector activation authority.

## Dependency order

1. `D0`: TASK-063 receipt-output overwrite, sibling-prefix containment, and
   ancestor-reparse corrections merge to canonical `main`, followed by
   post-main tests and installed read-back PASS.
2. `D1`: TASK-060 PP-A is integrated from fresh `main`, then PP-B and PP-C are
   canonically completed and expose exactly one promoted envelope plus source
   receipt.
3. `D2`: TASK-061 corrects its public-v1/private-v2 readiness dependency,
   completes CA-A through CA-C, and exposes Human one-shot activation and
   deactivation receipts plus exact disabled rollback read-back.
4. `D3`: TASK-065 proceeds in order `PL-A -> PL-B -> PL-C -> PL-D`.

TASK-059 signing is `NOT_REQUIRED` under the current contract. A future
explicit Release/Pack signing requirement is a separate Gate.

## Atomic Units

### PL-A — production linkage admission/projection

Pure, public-safe, effect-zero validation of the exact TASK-058, TASK-060,
TASK-061, and TASK-063 inputs. Missing, stale, tampered, ambiguous,
multi-instance, unknown-version, unknown-authority, or fixed-ProgramData
coordinates remain disabled and authorize no later effect.

### PL-B — installed SKILL config coordinate synchronization

Eligible only after current PL-A PASS and a separate Human/config Gate. It may
synchronize only the exact installed connector config coordinate with expected
revision/CAS. It must preserve the TASK-061-owned enabled bit and activation
history.

### PL-C — real connector E2E/read-back

Eligible only after PL-B. It runs `connector-status`, `publish-learning`, and
`load-profile` against the exact installed instance using public-safe synthetic
data. Runtime PASS requires exact request, BVP receipt, and independent Profile
read-back evidence; endpoint or file presence is insufficient.

### PL-D — lifecycle, rollback, and closure

Verify custom roots, upgrade, multiple installations, uninstall data
preservation, stale descriptor/config rejection, and disabled rollback. Final
closure requires independent DEV-4 Critic/Tester/Judge, focused/fault/relevant
regression, exact scope, canonical merge, and post-main read-back.

## Candidate Allowed Files

Repository-local candidate paths:

```text
docs/ai-team/tasks/TASK-065/**
src/ai_video_production/montage_learning_production_linkage.py
schemas/montage-learning-production-linkage.schema.json
src/ai_video_production/schema_resources/montage-learning-production-linkage.schema.json
tests/test_task065_montage_learning_production_linkage.py
tests/test_task065_montage_learning_production_linkage_windows.py
```

The following shared integration files are excluded from ordinary Units and may
change only at a milestone sole-Builder/LOCK checkpoint:

```text
docs/ai-team/task-index.md
docs/ai-team/current-state.md
docs/roadmap/PROJECT-ROADMAP-CANONICAL.md
CHANGELOG.md
```

The exact installed `bvp-montage-learning-adapter` connector config is an
external PL-B target behind a separate Human/config Gate. It is not a
repository-local Allowed File.

## Explicitly prohibited paths and effects

- `tests/test_task064_montage_learning_production_linkage.py` and
  `tests/test_task064_montage_learning_production_linkage_windows.py` are not
  TASK-065 paths and must not be created, edited, renamed, or copied.
- Do not modify TASK-058/060/061/063 source, schemas, tests, or historical
  Evidence.
- Do not modify TASK-036 Shell, TASK-044 Timeline, Resolve/DRFX source, other
  SKILLs, credentials, private keys, or Owner media.
- Do not restore a fixed ProgramData production Bridge fallback.
- Do not set the repository default connector config to enabled.
- Do not admit/promote learning, mutate Timeline/Resolve, Release, Deploy, or
  activate Production.

## Current mutation boundary

While D0 through D2 remain incomplete, only TASK-065-local design and test-plan
documents may change. Source, schema, tests, installed config, native state, and
production state remain mutation zero.

The frozen PL-A mapping, negative matrix, exact-path overlap audit, dependency
checklist, and focused fixture plan are in
`pl-a-admission-design-freeze-2026-08-30.md`.
