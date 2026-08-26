# TASK-029 R4 Owner Profile Registry Candidate — Design / Critic / Judge

Date: 2026-08-25

Governance: DEV-4 PRIVACY, LEARNING AND RELEASE INTEGRITY

## Atomic Unit

R3の暗号化Owner Profile Storeにmaterialize済みの最新Profile revisionを毎回exact再検証し、Model/Profile Registryへ登録する前のpure in-memory候補を作る。

本UnitはRegistryを作成・更新せず、Profileをruntime scoringへ適用しない。登録には本候補とは別の明示Human確認と後続Unitが必要である。

## Inputs and invariants

- sourceはR3 `OwnerProfileHistory`の最新revisionだけ。
- callerは読取時の`expected_history_revision`を指定し、現在revisionとの不一致をfail closedにする。
- R3 history、revision、materialization candidate、confirmation、proposal、binding、decision historyのhash lineageを保持する。
- Profile snapshotをTASK-008 `ScoringProfile`へ再構築し、rule、modality、weight合計、source selector、semantic version、canonical hashを再検証する。
- rollback coordinateはexact baseline profile hashと同一でなければならない。
- Owner scopeはbody-free SHA-256 coordinateだけを保持し、raw media、transcript、Prompt本文、host path、credentialを持たない。
- compatibilityは固定`TASK-008/SCORING_PROFILE/1.0.0` contractへ限定する。

## Outputs

- immutable `OwnerProfileRegistryCandidate`
- strict mirrored JSON Schema
- exact-source verifier
- state `READY_FOR_HUMAN_REGISTRY_REVIEW`
- `registry_candidate_sha256`

候補は以下を明示する。

- owner-local profile only
- latest Owner Profile history revalidation required
- explicit Human registry confirmation required
- in-memory candidate only
- Model/Profile Registry write authority false
- runtime Profile apply authority false
- Knowledge Pack / automatic promotion / rollback execution authority false
- Edit Plan / external effect authority false

## Threat and failure matrix

| Threat | Required result |
|---|---|
| empty Owner Profile history | reject |
| stale expected revision | reject |
| non-R3 history object | reject |
| candidate payload drift | reject |
| history/revision/materialization/confirmation lineage drift | reject |
| hash-consistent but semantically invalid Profile rule | reconstruct TASK-008 types and reject |
| rollback hash differs from baseline | reject |
| unknown/private body fields | schema/module surface reject |
| implicit Registry write or runtime activation | impossible from public API |

## Verification plan

- ready latest Profile exact projection and strict Schema validation
- deterministic recompilation and exact-source verification
- empty/stale/wrong-type negative matrix
- payload and history drift rejection
- recomputed-hash semantic-invalid Profile rejection
- immutable dataclass and schema mirror byte identity
- AST-based no-I/O/no-Store capability audit
- R2/R3 direct regression
- full TASK-019/029 regression and full Product regression before hosting

## Critic

Finding C/H/M before implementation review: 0 / 2 / 2.

Resolved High findings:

1. R3 hashes alone do not prove TASK-008 rule semantics after deserialization. R4 reconstructs `FeatureSourceSelector`, `FeatureRule` and `ScoringProfile`, then requires byte-equivalent canonical payload/hash.
2. A previously read Profile could become stale before registry review. R4 requires exact `expected_history_revision` and uses only the latest revision.

Resolved Medium findings:

1. Compatibility metadata could become caller-controlled. R4 fixes it to one TASK-008 contract constant.
2. A candidate could be mistaken for write/apply authority. Every write/apply/promotion/rollback/external flag is fixed false and the module has no I/O API.

Residual Critical/High/Medium: 0 / 0 / 0.

## Implementation Evidence

- R4 focused plus R2/R3 direct regression: 23 PASS
- TASK-019/029 learning/profile chain: 68 PASS
- full Product regression after final Critic hardening: 3688 PASS / 6 SKIP / 0 FAIL
- compileall, strict Schema JSON/instance validation, schema mirror and diff-check: PASS
- unresolved Critical/High/Medium findings: 0 / 0 / 0


## Judge

Decision: ACCEPT_IMPLEMENTATION_TESTED_COMMIT_READY.

Rationale: the Unit closes the verification gap between encrypted Owner-local Profile storage and future Registry admission without creating Registry mutation or runtime activation authority. Shared CHANGELOG integration remains a separate exact-lock transaction after the immutable implementation PR is hosted.
