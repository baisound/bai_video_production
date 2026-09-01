# TASK-060 -> TASK-061-A/B coordinated L2 design review manifest

Status: `EXACT_TECHNICAL_PREFIXES_FROZEN_V7 / REVIEW_PENDING / SOURCE_START0`

This administrative manifest freezes the three coordinated technical review
targets as one tuple. It creates no Product, Human, migration, Profile, config,
activation, release, deployment, native, or implementation authority.

## 1. Git coordinate

```text
repository: BAI VIDEO PRODUCTION
worktree: C:/home/baisound/projects/bai-video-production/.worktrees/platform-trust-delivery-corrective-design
branch: codex/platform-trust-delivery-corrective-design
worktree_head: 19c37245a1444f6f3ed5f3b707eeea94e68602b0
local_main_observed: 3223e47c5e570b0bf1776ba53e4e7513f1eccb57
origin_main_observed: 354ea2534ad5739a099d9eeaf0f1da9a7210ddb6
branch_relation: origin/main behind 22
source_test_schema_native_effect: 0
```

`origin/main_observed` is a currentness observation, not a rebase or source-start
authorization. Any later main change requires a fresh overlap/currentness Gate.

## 2. Exact technical prefixes

Ranges are zero-based half-open byte ranges over each exact UTF-8 file. All
three prefixes are LF-only (`CR=0`). The receipt/admin section beginning at the
named heading is outside the technical prefix and may record review results;
changing any byte inside a frozen prefix invalidates this manifest and requires
a new manifest revision and full coordinated review.

| Artifact | Frozen range | SHA-256 | Bytes | LF | Excluded admin heading |
|---|---:|---|---:|---:|---|
| `docs/ai-team/tasks/TASK-060/corrective-complete-design-packet.md` | `[0,163141)` | `43efab15620f0280e55cdd14da5cb9547487d382fd7d6c99569c844ceea94a7a` | 163141 | 1727 | `## 21. Design completion receipt template` |
| `docs/ai-team/tasks/TASK-061/preactivation-prepare-complete-design-packet.md` | `[0,170124)` | `3fcc4599b40f82cf5a06098bd94da153970ca4586632068bfff2d63e1c7a8472` | 170124 | 2258 | `## 22. Design completion receipt template` |
| `docs/ai-team/tasks/TASK-061/ca-a-b-c-limited-partition-amendment-design.md` | `[0,72292)` | `0b4575b4f9584abeae085659dcad248e4926c03a3fa9406208eb5cd3d9974f2b` | 72292 | 1090 | `## 14. Design receipt template` |

## 3. Cross-artifact tuple

The tuple preimage is UTF-8 without BOM, LF terminated, and is exactly:

```text
BVP:L2:COORDINATED-DESIGN-REVIEW:V7
worktree_head=19c37245a1444f6f3ed5f3b707eeea94e68602b0
origin_main=354ea2534ad5739a099d9eeaf0f1da9a7210ddb6
docs/ai-team/tasks/TASK-060/corrective-complete-design-packet.md|bytes[0,163141)|43efab15620f0280e55cdd14da5cb9547487d382fd7d6c99569c844ceea94a7a|163141|1727
docs/ai-team/tasks/TASK-061/preactivation-prepare-complete-design-packet.md|bytes[0,170124)|3fcc4599b40f82cf5a06098bd94da153970ca4586632068bfff2d63e1c7a8472|170124|2258
docs/ai-team/tasks/TASK-061/ca-a-b-c-limited-partition-amendment-design.md|bytes[0,72292)|0b4575b4f9584abeae085659dcad248e4926c03a3fa9406208eb5cd3d9974f2b|72292|1090
```

```text
tuple_sha256: 2429ef29d7a2c3eb484b78c026c3365f38963d03b6ab7d1f534544bb3ee23160
```

## 4. Reproduction rule

For each artifact, read raw bytes, locate the first exact UTF-8 admin heading,
hash bytes from offset zero up to but excluding that heading, and assert the
recorded byte and LF counts plus `CR=0`. Then concatenate section 3 exactly,
including its final LF, and SHA-256 that byte string. Any mismatch is
`NOT_REVIEWABLE`; no previous Critic/Tester/Judge result may be replayed.

Only `critic`, `tester`, `judge`, review-result references, and other receipt
administration below each excluded heading may change without invalidating the
technical tuple. Dependency placeholders remain dependency-N.C. and do not
create source-start authority.

## 5. Authority partition

This review Unit is docs-only and may change exactly these four files:

```text
docs/ai-team/tasks/TASK-060/corrective-complete-design-packet.md
docs/ai-team/tasks/TASK-061/preactivation-prepare-complete-design-packet.md
docs/ai-team/tasks/TASK-061/ca-a-b-c-limited-partition-amendment-design.md
docs/ai-team/tasks/TASK-061/l2-coordinated-corrective-design-review-manifest.md
```

Independent Critic/Tester `0/0` plus Judge PASS makes only one coordinated
docs-only Draft PR eligible. The review receipt has
`source_start_authority=false`; it cannot be copied, serialized, inferred, or
promoted into implementation authority.

A future separately authorized TASK-060 implementation Unit may modify exactly:

```text
src/ai_video_production/montage_preference_promotion_store.py
src/ai_video_production/montage_preference_source.py
src/ai_video_production/montage_preference_authority_operation.py
tests/test_montage_preference_promotion_store.py
tests/test_montage_preference_source_integration.py
tests/test_task060_montage_preference_authority_operation.py
docs/ai-team/tasks/TASK-060/corrective-complete-design-packet.md
```

A future separately authorized TASK-061-A implementation Unit may modify
exactly:

```text
src/ai_video_production/montage_learning_bridge_migration.py
src/ai_video_production/montage_learning_connector_activation.py
src/ai_video_production/montage_learning_preactivation_operation.py
tests/test_montage_learning_bridge_migration.py
tests/test_montage_learning_connector_activation.py
tests/test_task061_montage_learning_preactivation_operation.py
schemas/montage-learning-connector-activation.schema.json
src/ai_video_production/schema_resources/montage-learning-connector-activation.schema.json
docs/ai-team/tasks/TASK-061/preactivation-prepare-complete-design-packet.md
```

A future separately authorized TASK-061-B implementation Unit may modify
exactly:

```text
src/ai_video_production/montage_learning_connector_activation.py
src/ai_video_production/montage_learning_preactivation_operation.py
tests/test_montage_learning_connector_activation.py
tests/test_task061_montage_learning_preactivation_operation.py
schemas/montage-learning-connector-activation.schema.json
src/ai_video_production/schema_resources/montage-learning-connector-activation.schema.json
docs/ai-team/tasks/TASK-061/ca-a-b-c-limited-partition-amendment-design.md
docs/ai-team/tasks/TASK-061/preactivation-prepare-complete-design-packet.md
```

Every future implementation Unit requires its canonical dependency receipts,
a fresh canonical-main successor, fresh worktree/dirty/ownership/overlap/lock
proof, a separate implementation start receipt, and its own DEV-4 review. A
docs-only PASS cannot mint any of those prerequisites.

## 6. Review Gate

The three-prefix tuple must be reviewed together. One coordinated docs-only
Draft PR is eligible only after independent Critic and Tester report unresolved
Critical/High `0/0` on this exact tuple and Judge returns PASS. TASK-072 remains
separately owned and is consumed only through its future exact canonical
dependency receipt; this manifest modifies no TASK-072 artifact.

The old V6 reviews are historical only and have replay authority zero. Reviewers
must bind the exact V7 tuple and this manifest's exact frozen-prefix SHA-256.
Any technical-prefix or manifest-prefix change requires a new tuple and three
fresh reviews.

## 7. Administrative review receipt

```text
review_tuple_sha256: 2429ef29d7a2c3eb484b78c026c3365f38963d03b6ab7d1f534544bb3ee23160
manifest_review_target_range: bytes[0,7112)
manifest_review_target_sha256: 1f35ccc35bceca5071f4ba07f2b6e8c23c540ce34fd0a8e15b19a973efbdf2a6
manifest_review_target_bytes: 7112
manifest_review_target_lf_count: 143
manifest_review_target_cr_count: 0
critic: PASS_L_R2_V7_C_H_M_L_0_0_0_0_task061_l2_r3_sol_critic
tester: PASS_L_R2_V7_C_H_M_L_0_0_0_0_task060_r4_sol_tester
judge: PASS_L_R2_V7_C_H_M_L_0_0_0_0_task060_061_v7_independent_judge
unresolved_critical: 0
unresolved_high: 0
docs_only_draft_pr_eligible: true
source_start_authority: false
implementation_authority: false
release_authority: false
deploy_authority: false
production_activation_authorized: false
```
