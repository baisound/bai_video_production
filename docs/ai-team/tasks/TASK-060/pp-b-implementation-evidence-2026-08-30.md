# TASK-060 PP-B implementation candidate Evidence — 2026-08-30

## State and authority boundary

- Unit: `PP-B` — explicit Human confirmation and encrypted append-only
  promotion/rollback store.
- Branch: `codex/task-060-ppb-promotion-store`.
- Exact stacked base: PP-A candidate
  `6e16c3ea040c503137030d51ef965cc11545290b`.
- Canonical merge-base: audited `origin/main`
  `160c9569673fbf65a28b0f95eeb44c5b0111584f`.
- Development profile: `DEV-4 FOUNDATION CRITICAL`.

The Owner continuity/takeover instruction authorized work on an unfinished
dependency instead of treating it as an idle condition. This candidate remains
a Draft, noncanonical PP-B result. It grants no PP-C, connector, native,
Release, Deploy, Production, Timeline, Resolve, or automatic promotion or
rollback authority.

## Exact candidate scope

```text
docs/ai-team/tasks/TASK-060/pp-b-implementation-evidence-2026-08-30.md
docs/ai-team/tasks/TASK-060/task.md
schemas/montage-preference-projection-promotion.schema.json
src/ai_video_production/montage_preference_promotion_store.py
src/ai_video_production/schema_resources/montage-preference-projection-promotion.schema.json
tests/test_montage_preference_promotion_store.py
```

No TASK-019, TASK-029, TASK-055, TASK-058, Timeline, Resolve, connector,
registry, current-state, roadmap, CHANGELOG, installed SKILL, or external
configuration path is modified.

## Implemented contract

- A separate self-hashed Human confirmation binds the exact PP-A candidate,
  Owner scope, expected revision, predecessor hash, and active payload hash.
- Promotion re-runs the PP-A deterministic compiler against exact current
  source snapshots and policy while holding the cross-process update lock.
- The complete history is DPAPI-encrypted at rest with PP-B-specific entropy;
  only a checksum-closed, plaintext-free envelope is stored externally.
- Promotion and rollback revisions are append-only, contiguous, and hash
  chained. No revision is deleted or rewritten.
- Exact duplicate retries are no-op. Confirmation identity reuse, candidate
  replay under another confirmation, stale CAS, and scope collisions fail
  closed.
- Rollback is an explicit Human-confirmed higher revision which preserves the
  exact target envelope and target payload hash.
- Atomic replacement is followed by exact durable read-back. Failure before
  replacement leaves no target, while failure after replacement recovers as an
  exact duplicate no-op.
- Stored Profiles remain advisory-only. Timeline, Resolve, transport, runtime,
  and external effects remain `0`.

## Builder validation

Windows Python 3.12 focused tests, including real Current User DPAPI:

```text
python -m pytest -q -p no:cacheprovider \
  tests/test_montage_preference_projection.py \
  tests/test_montage_preference_promotion_store.py
24 passed
```

WSL2 Ubuntu focused tests, including cross-process serialization:

```text
python3 -m pytest -q -p no:cacheprovider \
  tests/test_montage_preference_projection.py \
  tests/test_montage_preference_promotion_store.py
23 passed, 1 skipped (Windows DPAPI runtime only)
```

Windows direct dependency regression:

```text
tests/test_task019_owner_decision_bridge.py
tests/test_task019_profile_tuning.py
tests/test_task029_human_edit_learning.py
tests/test_task029_owner_decision_store.py
tests/test_task029_owner_profile_materialization.py
tests/test_task029_owner_profile_registry_store.py
tests/test_task029_owner_profile_registry.py
tests/test_task029_owner_profile_store.py
75 passed
```

WSL2 direct dependency regression: `72 passed, 3 skipped`, with the three
skips limited to Windows DPAPI runtime tests. Windows `compileall`, schema
mirror identity, schema instance validation, and `git diff --check` pass.

## Remaining closure gates

- independent DEV-4 Critic, Tester, and Judge Evidence;
- hosted required-platform checks for the exact immutable commit;
- PP-B exact-head diff/scope review and Draft PR review;
- canonical merge and post-main read-back before PP-B is called complete;
- a separately bounded PP-C Unit before any production-source claim.
