# TASK-029 R2 Owner Profile Materialization — Design / Critic / Judge

- Date: 2026-08-25
- Governance: DEV-4 PRIVACY, LEARNING AND RELEASE INTEGRITY
- Base: fresh main 86bc114d1a3115cce8b65bee848dd0d2e48d788d
- Atomic Unit: pure Owner-wide Profile materialization candidate
- Hosted state: LOCAL_IMPLEMENTED / HOSTING_PENDING

## Authority and scope

The Owner moved TASK-029 ahead of the remaining Learning & Operations queue and authorized bounded autonomous implementation. This unit continues the same TASK-029 responsibility: convert exact admitted Human decisions into an Owner-local learning candidate.

MAY MODIFY:

- one pure TASK-029 materialization module;
- its public schema and byte-identical package mirror;
- focused tests;
- TASK-029 task/index/design records.

MUST NOT MODIFY:

- TASK-029 encrypted Owner Decision Store or its cipher/envelope;
- TASK-019 proposal or binding implementations;
- any Profile/Model Registry or Knowledge Pack store;
- Timeline, Resolve, media, Provider, Cloud, Release, Deploy, workflow, lock registry, or CHANGELOG before an exact hosted lock.

## Design

compile_owner_profile_materialization_candidate consumes only typed in-memory values:

1. exact TASK-019 ProfileTuningProposal;
2. exact TASK-019 ProfileTuningOwnerDecisionBinding;
3. latest TASK-029 OwnerDecisionHistory;
4. exact adjustment-to-decision selections.

The compiler reserializes and revalidates the history, then invokes the existing TASK-019 exact binding verifier. It emits a deterministic, immutable, body-free OwnerProfileMaterializationCandidate.

Only an all-ADOPTED READY_FOR_HUMAN_REVIEW binding may expose the exact proposed ScoringProfile snapshot. A non-ready proposal or any selected REJECTED decision emits profile_snapshot: null.

The candidate retains exact hashes for the history, proposal, binding, baseline, proposed profile, and rollback coordinate. It also records sorted distinct decision IDs. The proposed profile must differ from baseline, and rollback must equal baseline.

## Authority boundary

The candidate is review material, not an applied Profile. The schema fixes these authorities to false:

- Owner Profile Store write;
- Model/Profile Registry write;
- Knowledge Pack promotion;
- automatic promotion;
- rollback execution;
- Edit Plan mutation;
- external effect.

latest_history_revalidation_required, human_materialization_confirmation_required, and in_memory_candidate_only are fixed true. The module imports no filesystem, database, network, process, Store, cipher, Timeline, Resolve, media, or Provider capability.

## Failure modes

| Failure | Required result |
|---|---|
| proposal/binding/history/selection drift | reject before candidate creation |
| tampered candidate payload | exact verifier rejects |
| stale or malformed history | TASK-029 history reconstruction rejects |
| missing/duplicate/unknown support | TASK-019 binding verifier rejects |
| non-ready proposal | no Profile snapshot |
| selected REJECTED decision | no Profile snapshot |
| baseline equals proposed | reject |
| rollback differs from baseline | reject |
| caller attempts mutation | frozen dataclass rejects |

## Critic review

- Finding: directly loading the encrypted Store would widen plaintext exposure and duplicate Store responsibility.
  - Resolution: accept only a typed in-memory history and import no Store/cipher API.
- Finding: a READY binding could be confused with write authority.
  - Resolution: name the output a candidate, require a separate Human materialization confirmation, and fix every effect flag false in both code and schema.
- Finding: a stale history could be paired with an older binding.
  - Resolution: reconstruct the supplied history and exact-verify the binding against it on every compile.
- Finding: future Knowledge Pack promotion could be accidentally implied.
  - Resolution: Pack promotion and Registry writes remain explicit later Atomic Units and are not exported here.

Unresolved Critical/High findings: 0 / 0.

## Tester evidence

- focused R2 tests: 8 PASS;
- required combined TASK-019/TASK-029 regression: 53 PASS;
- full regression: 3673 PASS / 6 SKIP / 0 FAIL;
- schema mirror byte identity and bounded seven-file diff scope: PASS.

## Judge decision

ACCEPT_LOCAL_COMMIT_READY.

Conditions for commit-ready:

1. focused and combined regressions pass;
2. public/package schemas remain byte-identical;
3. no I/O or Store capability appears in the module;
4. diff contains only the bounded seven files plus no Owner-owned tmp/;
5. hosted integration follows the dedicated exact CHANGELOG lock transaction.

This decision creates no Profile write, promotion, rollback, Release, Deploy, or Production authority.
