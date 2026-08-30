# TASK-060 Owner Allocation and Implementation Authorization Boundary

## Decision

- Task allocation: `TASK-060`
- Capability: `BVP-MONTAGE-PREFERENCE-PROJECTION-001`
- Metadata result: `ALLOCATION_BOUND / IMPLEMENTATION_NOT_AUTHORIZED`
- Development profile: `DEV_4_FOUNDATION_CRITICAL`
- Review/fix budget: maximum `2` cycles, then Owner escalation

This document is an immutable candidate authorization record. It defines the
only scope that a later canonical implementation authorization may activate;
it is not itself permission to mutate implementation files.

Current metadata effect is exactly: task-index `0`, Registry `0`, source `0`,
schema `0`, test `0`, connector activation `0`, runtime/native/paid/external
execution `0`, and Release/Deploy/Production `0`.

## Bound authority coordinates

- Accepted design commit: `0ac8971174ab227a6f62b8b797307bbc31b70145`
- Accepted design SHA-256: `sha256:c54623039fc8197c6bf8d02d5363ae53b601e4feef400243fa8be1f4b2280353`
- Canonical BVP base: `e78699bc14f23abce995a46a9b059f826f9c2ef1`
- Registry revision: `128`
- Reservation lock: `BVP-INTEGRATION-LOCK-TASK060-TASK062-AUTHORIZATION-METADATA-20260827`
- Target branch: `codex/task-060-task062-authorization-metadata`
- Preflight: Task/tree/index/Registry/roadmap collision `0`; open-PR exact-path overlap `0`

Any design, main, Registry, lock, branch, blob, or scope drift expires this
candidate and requires a new exact Owner Gate.

## Objective and Atomic Units

Produce an advisory-only v1 envelope from independently reopened TASK-029 and
TASK-019 canonical sources without LLM inference or TASK-055 timing conversion.

| Unit | Goal | Mandatory gate |
|---|---|---|
| `PP-A` | Typed versioned projection policy and pure deterministic candidate compiler | schema/contract/negative tests PASS |
| `PP-B` | Explicit Human confirmation and append-only promotion/rollback store | CAS/fault/recovery tests PASS |
| `PP-C` | Pinned read-only production source port returning the exact promoted envelope | drift/scope/tamper tests PASS |

Order: `PP-A -> PP-B -> PP-C`.

## Closed future implementation Allowed Files

No other path is permitted by this authorization boundary:

```text
src/ai_video_production/montage_preference_projection.py
src/ai_video_production/montage_preference_promotion_store.py
src/ai_video_production/montage_preference_source.py
src/ai_video_production/montage_learning_connector_readiness.py
src/ai_video_production/__init__.py
schemas/montage-preference-projection-policy.schema.json
schemas/montage-preference-projection-promotion.schema.json
src/ai_video_production/schema_resources/montage-preference-projection-policy.schema.json
src/ai_video_production/schema_resources/montage-preference-projection-promotion.schema.json
tests/test_montage_preference_projection.py
tests/test_montage_preference_promotion_store.py
tests/test_montage_preference_source_integration.py
docs/ai-team/tasks/TASK-060/task.md
docs/ai-team/tasks/TASK-060/task060-owner-allocation-and-implementation-authorization-2026-08-27.md
```

`montage_learning_connector_readiness.py` may receive only the narrow sealed
production-source binding seam after TASK-058 B+C is canonically closed. A
required edit to any other TASK-058 path is a stop condition.

## Dependencies and non-overlap

- Reopen and independently verify current TASK-029 Owner Profile Registry,
  Profile History, and Owner Decision History records.
- Reopen and independently verify exact TASK-019 proposal, Owner decision
  binding, promotion, and rollback records.
- Do not use TASK-055 `MontagePreferenceProfile`, timing median, event/music
  anchors, raw transcript, or media observations.
- Do not implement TASK-058 bridge, intake, receipt, transport, or readiness
  behavior except the single sealed source-binding seam named above.
- Do not create a second canonical Timeline or automatic learning authority.

## Acceptance and required validation

- exact public policy schema/package mirror byte identity;
- duplicate/missing mapping, wrong sign, token, and unknown-version rejection;
- integer golden vectors at zero, half, threshold, and cap with no negative zero;
- latest-change reconstruction across multiple source revisions;
- distinct adopted Human decision per feature and no decision replay;
- rejected, revoked, stale, `DO_NOT_LEARN`, Safety, and Rights negatives;
- mixed Owner, private Project-only request, scope, and source-revision drift negatives;
- custom Mapping/scalar hook count zero and immutable input snapshots;
- deterministic candidate, envelope payload, and stable identity hashes;
- promotion duplicate/collision/CAS and cross-process serialization;
- DPAPI synthetic round-trip, wrong cipher, tamper, and plaintext scan;
- crash recovery before/after replace and before durable read-back;
- rollback only as a higher promotion revision preserving target payload hash;
- pinned production-source read with path substitution and reparse negatives;
- byte/semantic-equivalent v1 envelope at the TASK-058 boundary;
- Timeline, Resolve, automatic adoption/promotion, Provider, and external effects `0`;
- focused tests, TASK-019/TASK-029 direct regression, schema mirror, compile,
  diff check, and final full BVP regression PASS.

Command families to freeze per Atomic Unit:

```text
python -m pytest -q -p no:cacheprovider tests/test_montage_preference_projection.py tests/test_montage_preference_promotion_store.py tests/test_montage_preference_source_integration.py
python -m pytest -q -p no:cacheprovider tests/test_task019_owner_decision_bridge.py tests/test_task019_profile_tuning.py tests/test_task029_human_edit_learning.py tests/test_task029_owner_decision_store.py tests/test_task029_owner_profile_materialization.py tests/test_task029_owner_profile_registry_store.py tests/test_task029_owner_profile_registry.py tests/test_task029_owner_profile_store.py
python -m compileall -q src tests
python -m pytest -q -p no:cacheprovider
git diff --check
```

Nonexistent future focused test paths become executable only after their owning
Unit creates them; this metadata Unit does not run or claim those tests.

## DEV-4 role separation

- Builder: implements only one authorized PP Unit and supplies exact-head evidence.
- Critic: independently reviews contracts, failure modes, scope, privacy, and authority.
- Tester: independently executes focused, fault, dependency, and regression suites.
- Judge: accepts only exact immutable Evidence with unresolved Critical/High `0/0`.

No role creates Owner authority. Builder output is not independent Tester
Evidence. Hosted and post-main results remain separate from local evidence.

## Prohibited effects and stop conditions

Prohibited: TASK-055 schema/source changes; TASK-058 bridge receipt/store
changes; Timeline/Resolve code; CHANGELOG or Registry mutation without a later
dedicated lock; Product Project or real Owner data; repository/production
connector config; provider credentials; paid/native/external execution;
Release, Deploy, Production activation; automatic retry or rollback.

Stop on source API/schema drift, a new owning Task, ambiguous Owner scope,
incomplete history, float-dependent canonical output, need for additional public
envelope fields, private/raw data, dirty or unknown ownership, shared-lock
conflict, Allowed Files expansion, or any request to auto-apply a preference.

## Expiry and revocation

This boundary expires on accepted-design mismatch, canonical-main or Registry
drift not explicitly revalidated, Task/branch/PR/path collision, six-document
blob drift, Critical/High finding, dependency revocation, Owner revocation, or
forbidden side effect. Activation requires a later canonical amendment binding
the exact PR HEAD, all six metadata blob hashes, Hosted checks, DEV-4 `0/0`, and
the Owner Ready/merge decision.
