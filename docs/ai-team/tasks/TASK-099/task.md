# TASK-099 — Project / Job Currentness V2 successor

- Status: `JCV_D_R0_DESIGN_ACCEPTED / JCV_I_RECOVERY_R1_ACCEPTED_COMPLETE / JCV_N_D_R1_DESIGN_ACCEPTED_TASK102_DEPENDENCY_ALLOCATED / CANONICAL_INTEGRATION_PENDING`.
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

## JCV-I cycle-2 recovery checkpoint — 2026-09-27

- Worktree: `C:\home\baisound\projects\bai-video-production\.task047-status-sync-20260924`; branch `codex/task-073-expression-master-wav-plan`; base/current HEAD `b43339e7592864548ee39c33095e05ff657482d9`; bound main `e41110c85ba4ab098c591378cb1b2eaae3cc3cb7`.
- Exact4 frozen SHA-256: source `0d5813c8cd579ce654fb9974d47629d1af080d7c953c89a4521e361d2ebb4faf`; canonical schema and package mirror `121b107f4fc4b30f28d8a827661e6b2bb6236abdaa8786a702fd44a23621ebf9`; tests `fe803ba1f4481fc15f8c3042e8bad1d8a8350944d732a1e0e8d408ef7d05a86c`.
- Parent verification: `83 passed` for TASK-099 plus three direct TASK-043 suites; Python compilation, JSON/schema self-check within pytest, mirror equality and `git diff --check` passed. No native, Product, filesystem backend, private voice, model, release, deploy or Production effect occurred.
- Independent cycle-2 Tester: `REJECT`, C/H/M/L `0/1/0/0`; prior five High probes repaired, 16 focused functions passed. Remaining High: COMMIT `SAME_OPERATION_NOT_COMMITTED` plus `no_manifest_write_proven=true` can be classified no-write even when the same envelope says `manifest_commit_observation=COMMITTED`; contradictory evidence must query or become UNKNOWN.
- Independent cycle-2 Critic/Judge: `REJECT`. In addition to the same commit-observation contradiction, it reproduced PUBLISH status/payload contradiction reaching commit, known committed/superseded history being downgraded by a later no-commit query, and release failure masking a determined commit result.
- DEV-4 maximum two review/fix cycles is exhausted. JCV-I is not commit-ready or complete. No commit was created. JCV-N/JCV-C remain unauthorized. Resume only through an explicit Recovery unit that freezes phase-envelope cross-field invariants, monotonic same-operation knowledge and release-warning result behavior before another implementation/review decision.

## JCV-I Recovery R1 authority and frozen correction design

- Owner authorization: 2026-09-27, explicit approval to start `Recovery R1` after the cycle-2 rejection checkpoint.
- Scope remains the accepted JCV-I exact5. This is not JCV-N, native/backend implementation, Product integration, audio/model work, release, deploy or Production authority.
- Phase cross-field invariant: phase status, payload discriminator, `manifest_commit_observation`, `no_manifest_write_proven` and nullable successor identities must form one accepted combination. Contradictory combinations fail closed before any later mutation phase.
- Same-operation knowledge is monotonic. Once COMMIT or QUERY provides authenticated evidence that the operation committed, no later no-commit response may downgrade it to `CONFLICT_NO_WRITE`; superseded commit remains `COMMIT_OUTCOME_UNKNOWN / COMMITTED / SUPERSEDED_PRESERVED`.
- Release is cleanup evidence, not permission to erase an already determined transaction outcome. Release failure or `RELEASE_WARNING` appends `LEASE_RELEASE_WARNING` while preserving the determined committed/unknown/no-write result and fixed false authority flags.
- Initial request admission may compare the request timestamp with the opened observation interval. REREAD and successor evidence acquired later must not be rejected merely because `observed_at` is after `requested_at`; JCV-I instead requires non-regressing authenticated observation sequence/time and relies on the admitted trusted backend/currentness capability. Native trusted-now enforcement remains JCV-N responsibility.
- Recovery R1 acceptance requires focused cross-field/monotonic/release/fresh-observation negatives, direct TASK-043 regression, exact4 freeze, and a fresh independent DEV-4 Critic/Tester/Judge decision.

## JCV-I Recovery R1 final acceptance

- Frozen exact4 SHA-256: source `9d2a3bd5c0e5b225f650e283a8e65df79b31b52f0ef8933287317faa8c3ee523`; canonical schema and package mirror `8a72e5a6fcc528faa12b56ab944a97fda697ac7354961cc9702a934e2d43897b`; tests `a23ab77df21c14aebd258fcc09af16b0a8e28bb09188709ff95e6a09e03bb6aa`.
- Parent verification: TASK-099 focused plus direct TASK-043 regression `88 passed`; Python compilation, schema validation/mirror equality and `git diff --check` PASS.
- Independent Tester: `PASS / ACCEPT`, C/H/M/L `0/0/0/0`; focused functions 21 PASS plus bounded contradiction, monotonicity, release and observation probes.
- Independent Critic/Judge: `ACCEPT`, C/H/M/L `0/0/0/0`; independent memory probes 10 PASS and focused pytest 22 PASS.
- Accepted responsibility: strict bounded JCV-I schemas/parsers, deterministic currentness-index compilation, result/public projection and side-effect-injected fake-port orchestration only.
- Explicit non-acceptance: no JCV-N secure native backend, filesystem/path/lock/replace implementation, live trusted currentness, Product consumer integration, private voice/media processing, model/training, release, deploy or Production authorization. TASK-099 remains open for separately authorized JCV-N and JCV-C.

## JCV-N-D R0 design unit

- Owner continuation: 2026-09-27 `つぎへ`, interpreted as authority to perform the next design/review gate only after JCV-I acceptance; no native/service/ACL/filesystem effect authority is inferred.
- Design: `jcv-n-d-secure-native-backend-r0.md`.
- Exact design files: this Task record and the design document. Source/tests/native effects remain prohibited until design acceptance and the recorded Human architecture decision.
- Current feasibility finding: TASK-068 is immutable-only and the legacy TASK-043 store cannot prove the required physical predecessor CAS against an uncooperative same-user writer. R1 therefore proposes a service-SID Secure Project Manifest Transaction Broker while retaining `.bai-project/project.json` as the sole canonical selector. Because protecting `.bai-project` affects every manifest writer, this generic broker cannot belong to TASK-099; Owner architecture acceptance and a new direct dependency Task are required before JCV-N implementation allocation.
- R0 independent review was `REVISE`: Critic/Judge C/H/M/L `0/2/1/0`, Tester `0/4/2/0`. R1 adds operation-bound durable non-selector witnesses with restart reconciliation before later writes, protected owner/DACL plus long-lived sharing barriers, mutually pinned pipe process identity and connection-local capability, an API-specific Windows feasibility gate, explicit private IPC/public projection separation, and full manifest-writer/TASK-068 security inventory requirements. No native feasibility is claimed until R1 rereview and the dependency's own proof gates pass.
- R1 independent rereview: Critic/Judge `ACCEPT`, C/H/M/L `0/0/0/0`; Tester `PASS / ACCEPT`, C/H/M/L `0/0/0/0`. Accepted scope is the architecture contract, responsibility separation and feasibility/test gates only. Windows CAS/durability, service/ACL behavior, TASK-068 native composition, enrollment and runtime remain `NOT_CONFIRMED` and unauthorized.
- Owner decision: accepted introduction of the service-SID Secure Project Manifest Transaction Broker and allocation of TASK-102 as the new direct dependency for its generic canonical-store responsibility by answering `つぎへ` directly to the explicit gate. The decision authorizes allocation/design and separately bounded pure work only; it does not authorize service installation, ACL mutation, native QA, release, deploy or Production.
- JCV-N dependency: TASK-102 must accept its protocol/journal/witness design, prove the Windows security/replacement/durability boundary and migrate every Project manifest writer/recovery route before JCV-N native integration. TASK-068 immutable publication remains an independent prerequisite.
