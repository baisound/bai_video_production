# TASK-099 — Project / Job Currentness V2 successor

- Status: `JCV_D_R0_DESIGN_ACCEPTED / JCV_I_PURE_IMPLEMENTATION_ELIGIBLE / JCV_N_NATIVE_NOT_AUTHORIZED / CANONICAL_INTEGRATION_PENDING`.
- Governance: DEV-4 FOUNDATION CRITICAL.
- Owner intent: 2026-09-27 expression Master WAV remaining-Task/detail-design request.
- Responsibility predecessor: TASK-043 hosted-closed; historical implementation is not reopened.
- Coordinator: TASK-073 delivery plan. Canonical responsibility: Product Project currentness, not Job event ownership.
- Delivery owner: this voice-integration thread `01a054d9-2cf9-71e2-a486-351727c13150`, by the Owner's explicit two-contract takeover instruction. Own design -> implementation -> tests/review -> canonical handoff; no reassignment gate. Implementation intent is authorized, but exact files/unit and native authority must be bound before effects.
- Allocation serialization: ID99 is unused in bound main `e41110c8`; fresh ID/lock audit before integration. No source/runtime authority is created.
- JCV-D R0 exact design files: this task definition and `jcv-d-project-job-currentness-v2-r0.md`. No source/native/runtime effect. Prospective source/schema/tests require independent JCV-D acceptance and the exact-files allocation recorded below.

## Required design

Provide the private `PROJECT_JOB_CURRENTNESS_READBACK_V2` required by TASK-076 complete-design-packet §7.7. Bind opened Project root/manifest physical identity and canonical bytes, Project ID/revision/predecessor, exact Job semantic key, typed `ABSENT_JOB_HEAD` or `SELECTED_JOB_HEAD` with event coordinate/hash/physical identity, TASK-068 namespace/plan-set digest, consumer/save operation, install/build/security/reader identity and trusted monotonic currentness coordinate.

TASK-076 owns candidate immutable Job events; TASK-099 owns selection by secure Project manifest transaction. First reservation consumes exact absence proof; later commits consume exact selected predecessor. Under an accepted secure transaction/locking design, revalidate Project and candidate identities, compare prior revision/head, commit one successor revision, then return a fresh exact readback. A pre-commit crash leaves prior selected state; a post-commit interrupted readback is uncertain until exact re-read, never blind replay. No scan-derived latest winner, equal-ID/hash substitute, arbitrary manifest rewrite, generic legacy lock or AtomicJsonWriter-as-proof.

TASK-068 provides only its accepted I/O scope; missing mutable-manifest atomicity/CAS/physical identity support must be resolved in this producer's reviewed backend contract, not inferred from immutable JSON helpers. TASK-072 retains live child containment; TASK-076 retains durable Job state/event/recovery. This is a versioned successor port, not a V1 alias or second Project store.

### Proposed closed readback and transaction contract for JCV-D

Private readback fields: `contract_version=PROJECT_JOB_CURRENTNESS_READBACK_V2`, `project_id`, `manifest_revision`, `manifest_sha256`, nullable `predecessor_manifest_sha256`, `manifest_physical_identity_ref`, `project_root_identity_ref`, `job_semantic_key_sha256`, `head`, `namespace_plan_set_sha256`, `consumer_operation_id`, `install_build_binding_sha256`, `security_reader_binding_sha256`, `trusted_currentness_coordinate`, `readback_sha256`. `head` is a strict union: `ABSENT_JOB_HEAD` carries the opened manifest revision/hash and exact semantic-key absence proof; `SELECTED_JOB_HEAD` carries event coordinate/hash/physical-identity reference and selected predecessor. Null means not applicable only in the explicit union, never unknown proof. Physical/clock refs are opaque private trusted-port references, not caller-authenticated strings. Public projection is status/digest only.

Transaction request binds exact prior readback digest/coordinate, exact immutable TASK-076 candidate readback/event/semantic-key, next manifest binding proposal and one consumer operation. Legacy Project ID/revision/hash-only input is not accepted. Secure backend port must provide pinned Project ancestor/manifest identities, bounded strict read, accepted sole-writer exclusion, predecessor CAS, durable commit/readback, trusted monotonic identity/currentness and crash classification. The pure parser can validate structure/bindings but cannot mint authentic readbacks; synthetic ports return `FIXTURE_ONLY`, never `CURRENT` live capabilities.

Algorithm: pin/open Project and candidate -> validate strict bounded canonical manifest/event/schema -> acquire accepted exclusive physical transaction -> re-read/revalidate same Project and expected prior head -> compare exact revision/currentness/candidate -> write validated next manifest through reviewed secure commit -> durable commit classification -> re-open fresh exact readback under the selected successor -> release transaction. Outcomes are `COMMITTED_WITH_READBACK`, `CONFLICT_NO_WRITE`, `BLOCKED_NO_WRITE`, or `COMMIT_OUTCOME_UNKNOWN`; UNKNOWN is not success or permission to retry. Recover by the same operation identity and exact selected successor; if candidate is only an orphan, preserve it without selection. No reset/deletion/repair of an uncertain foreign path.

The backend is not available just because the legacy `product_project_store.py` has CAS under a generic lock. No path-based native implementation starts until JCV-D resolves and independently reviews these exact secure ports with TASK-068's existing successor lane. This is one existing Project-store extension, not a parallel manifest.

## Atomic Units / exit

1. JCV-D: freeze schema, physical security/transaction/trusted-time ports, complete crash/recovery matrix and exact source allocation; independent Critic/Tester/Judge.
2. JCV-I: proposed exact implementation payload is four files: `src/ai_video_production/task099_project_job_currentness.py`, `schemas/task099-project-job-currentness.schema.json`, its `src/ai_video_production/schema_resources/` mirror and `tests/test_task099_project_job_currentness.py`; this Task record is the fifth allowed completion-status carrier. Pure schema/parser and fake-port fault/concurrency tests only. JCV-D independent acceptance/fresh-main audit binds this exact5 before mutation. Legacy Project manifest/store/native backend and consuming owners remain outside that first source unit.
3. JCV-N: separately authorized secure native backend, physical identity/reparse/replace/ABA/concurrent writers/expiry/currentness tests; persist/read back Evidence.
4. JCV-C: TASK-076/074/072 consumer amendment and current canonical readback; no canonical owner transfer.

Exit: required V2 producer source and schema mirrors, independent DEV-4 review, exact-version consumer negatives, same-head required tests/checks and observed native transaction/readback. Design-only completion is not this Task's delivery completion. Forbidden: inference, playback, training, model custody, paid/cloud, installation, release/deploy/Production, OS mutation and historical TASK-043 edits.

See [delivery plan](../TASK-073/expression-master-wav-delivery-plan-r0.md) for scope, gates and order.

## JCV-D R0 independent decision

- Accepted design: `jcv-d-project-job-currentness-v2-r0.md`.
- Accepted design SHA-256: `80cc45d14c6251a1f3c6b90b77f8ce764fc4b3a0851750732ff9ff9b66f2a99d`.
- Independent DEV-4 Critic/Judge after one bounded correction cycle: `ACCEPT`, final C/H/M/L `0/0/0/0`.
- Independent design Tester: `PASS`; both frozen NUL-domain digest vectors were independently reproduced and all prior High/Medium findings were closed.
- Closed findings: missing profile/predecessor/operation/build/security comparison fields; undefined first-index transition; unsafe superseded-commit NO_WRITE classification; post-commit drift contradiction; exact successor-manifest preservation; fixture/live separation; committed-state versus observation freshness; proposal-validation phase; nested envelope bounds; normative digest preimages.
- JCV-I is eligible only for the exact five paths recorded above and pure/fake-port behavior. Legacy Project manifest/store changes, path/native backend, migration, live currentness, JCV-C consumers and all Product/native effects remain unverified and separately gated.
