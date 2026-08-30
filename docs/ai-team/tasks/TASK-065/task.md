# TASK-065 — Production Montage Learning Linkage Closure

- Status: `ALLOCATED / PRE_IMPLEMENTATION_DEPENDENCY_GATED`
- Capability: `BVP-PRODUCTION-MONTAGE-LEARNING-LINKAGE-001`
- Development profile: `DEV-4 FOUNDATION CRITICAL`
- Canonical audit base: `35cdf1ad475633dcf035e0616e979b5a8fde0c88`
- Owner request: establish the production SKILL-to-BVP linkage under the canonical rules without interrupting or reassigning the three active development lanes.
- Owner design correction: `2026-08-31` — Option B; the canonical and installed
  SKILL distribution config remains unchanged. Runtime selection uses only a
  BVP-owned, instance-bound config projection passed through explicit
  `--config`.

## Objective

Consume, without taking ownership from them:

- TASK-058 released SKILL interchange and Bridge transport;
- TASK-060 PP-C exact promoted advisory Preference source;
- TASK-061 CA-C Human activation/deactivation and config history;
- TASK-063 installer-selected-root-relative instance and discovery evidence.

TASK-065 closes production coordinate synchronization and real read-back/E2E.
It does not reimplement Timeline/Resolve ownership, learning admission,
Preference promotion, or connector activation authority.
It does not edit or synchronize the canonical/installed SKILL distribution
config. The historical fixed-ProgramData default remains disabled and is never
an active production fallback.

## Dependency order

1. `D0`: TASK-063 receipt-output overwrite, sibling-prefix containment, and
   ancestor-reparse corrections merge to canonical `main`, followed by
   post-main tests and installed read-back PASS.
2. `D1`: TASK-060 PP-A is integrated from fresh `main`, then PP-B and PP-C are
   canonically completed and expose exactly one promoted envelope plus source
   receipt.
3. `D2`: TASK-061 corrects its public-v1/private-v2 readiness dependency and
   supplies CA-A/CA-B plus a sealed CA-C prepare/Human one-shot candidate with
   apply effect zero. The current candidate cannot mint the real-installed E2E
   receipt required by ACTIVATE, so a separately authorized TASK-061 amendment
   or successor is required before the cycle below can execute.
4. `D2C`: a separately authorized TASK-058 owner supplies a public sealed
   read-only current-coordinate receipt for the Generic review store. It binds
   the current ledger revision to the Project manifest/binding, ledger head,
   recovery/journal currentness with no-create/read-only semantics. It exposes
   only the fixed Generic admission surface; exact APIs remain sealed. Until
   that owner allocation and completion receipt exist, this dependency is
   `N.C.`.
5. `D2P`: TASK-036/Development 2 supplies a bounded private Product-operation
   entrypoint in the unified packaged EXE plus its focused-verification
   completion receipt. It consumes D2C and does not inspect TASK-058 private
   storage helpers or raw ledger JSON.
6. `D3`: TASK-065 proceeds through `PL-A`, then the cycle-safe sequence
   `CA-C prepare (apply0) -> PL-B0 -> PL-C0 -> CA-C apply -> PL-B steady-state
   -> PL-C steady-state -> PL-D`.

`PL-B0` is a sealed, explicit-path, pre-activation E2E config candidate and
`PL-C0` is public-safe synthetic transport E2E against the exact real installed
instance. Neither is Production activation. CA-C alone consumes the exact PL-C0
receipt and owns activation/history mutation. TASK-065 never changes TASK-061
source or mints Human authority.

TASK-059 signing is `NOT_REQUIRED` under the current contract. A future
explicit Release/Pack signing requirement is a separate Gate.

## Atomic Units

### PL-A — production linkage admission/projection

Pure, public-safe, effect-zero validation of the exact TASK-058, TASK-060,
TASK-061, and TASK-063 inputs. Missing, stale, tampered, ambiguous,
multi-instance, unknown-version, unknown-authority, or fixed-ProgramData
coordinates remain disabled and authorize no later effect.

### PL-B — BVP-owned instance-bound runtime config projection

Eligible only after current PL-A PASS and a separate Human/config Gate. It may
publish only a revisioned BVP-owned runtime config projection beneath the exact
TASK-063 installer-relative Bridge state. It binds the exact install instance,
descriptor/owner identities and current TASK-061 config/history receipt. The
adapter is always invoked with the exact read-back operation config path through
`--config`; default discovery and fixed-ProgramData fallback are forbidden.

Steady-state `enabled` is derived only from the current TASK-061 activation
receipt/history. PL-B cannot edit that history, mint Human evidence, or infer
enabled state. PL-B0 requires the separately authorized TASK-061 pre-activation
E2E ticket described in the correction packet and never publishes a steady-
state runtime config. Every pre-activation and steady-state runtime config fixes
`require_admission_receipt:true`; publish/read feature flags are operation-
scoped minimum authority and are never assumed both true.

### PL-C — real connector E2E/read-back

PL-C0 runs the bounded pre-activation public-safe synthetic transport flow only
after PL-B0 and after the TASK-061 operation-plan/admission receipt plus the
TASK-058 current-coordinate receipt and TASK-036 packaged-entrypoint completion
receipt are current. It returns the exact E2E receipt to TASK-061 and claims no
Production activation. After CA-C
apply and steady-state PL-B projection, PL-C runs
`connector-status`, `publish-learning`, and `load-profile` against the exact
installed instance using explicit `--config`. Runtime PASS requires exact
request, BVP receipt, TASK-061 activation/config identity and independent
Profile read-back evidence; exit zero, endpoint or file presence is
insufficient. The bounded Product operation uses only the generic review-
observation lane; raw Project/anchor paths, revisions, store IDs or Owner scope
from caller text are prohibited.

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

The canonical and installed `bvp-montage-learning-adapter` connector configs
are not PL-B targets and remain byte-unchanged. Future PL-B runtime artifacts
are BVP-owned state effects, not repository files, and remain behind separate
Human/config/native gates. Their exact coordinates and transaction contract are
frozen in `pl-b-option-b-runtime-config-design-correction-2026-08-31.md`.

## Explicitly prohibited paths and effects

- `tests/test_task064_montage_learning_production_linkage.py` and
  `tests/test_task064_montage_learning_production_linkage_windows.py` are not
  TASK-065 paths and must not be created, edited, renamed, or copied.
- Do not modify TASK-058/060/061/063 source, schemas, tests, or historical
  Evidence.
- Do not modify TASK-036 Shell, TASK-044 Timeline, Resolve/DRFX source, other
  SKILLs, credentials, private keys, or Owner media.
- Do not modify the canonical or installed SKILL distribution config, including
  its historical disabled fixed-ProgramData default.
- Do not restore a fixed ProgramData production Bridge fallback.
- Do not invoke the adapter without the exact read-back BVP-owned `--config`
  path or let it discover/use the distribution default.
- Do not create a pre-activation enabled config without a separately authorized
  TASK-061 one-shot E2E ticket and bounded PL-C0 Gate.
- Do not construct or unseal `InstalledAdapterE2EReadback` privately, bypass its
  canonical TASK-061 factory, add a watcher/automatic importer, or implement a
  TASK-036 Product-operation entrypoint from TASK-065.
- Do not call TASK-058 private Generic-store loaders, parse raw ledger JSON, or
  accept a caller/CLI-provided expected revision as a current coordinate.
- Do not use Bridge state as a shared dummy external anchor, create Project
  authority directories during a status/readback operation, or expose TASK-058
  exact APIs through the Generic-only facade.
- Do not accept a missing or `REJECTED` admission receipt, extra public-receipt
  fields, or correlation/instance/source/config hash mismatch as E2E or
  activation evidence.
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
