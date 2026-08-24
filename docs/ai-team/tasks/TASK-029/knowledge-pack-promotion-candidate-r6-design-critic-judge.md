# TASK-029 R6 Knowledge Pack Promotion Candidate — Design / Critic / Judge

Date: 2026-08-25

Governance: DEV-4 PRIVACY, LEARNING AND RELEASE INTEGRITY

Atomic Unit: pure cross-Owner / cross-Project Knowledge Pack promotion candidate

## Context scope

- MUST READ: TASK-029 canonical task, R0 Human Action Evidence, R1 Owner Decision History, R5 Owner Profile Registry History, TASK-008 FeatureRule, exact schemas/tests.
- MAY MODIFY: one new pure TASK-029 module, its schema/mirror/tests, this design record, TASK-029 task status and task-index status.
- MUST NOT MODIFY: R0-R5 stores or schemas, TASK-019/TASK-008 source, current-state while open PR overlap exists, CHANGELOG/Lock registry/workflows, Timeline/Resolve/Provider/Cloud/Release/Deploy paths.

## Goal

Create a deterministic in-memory candidate for one common FeatureRule only when independently Human-adopted learning sources reproduce across distinct Owners and Projects. The candidate is Evidence for later Human review and independent Critic only. It is not a Knowledge Pack, signature, Git write, promotion, runtime apply, release, or rollback authority.

## Source binding

Each source contains exactly:

1. one typed R5 `OwnerProfileRegistryHistory`;
2. the exact R1 `OwnerDecisionHistory` whose history hash is bound by the latest registered Profile revision;
3. one ADOPTED decision ID included in that active registered Profile lineage;
4. the exact typed R0 `HumanActionEvidence` rows whose hashes are stored by that decision.

The compiler reconstructs both histories through their strict `from_dict` validators before use. It requires one source per Owner, exact Owner scope agreement, exact decision-history hash agreement, exact decision ID membership, exact Evidence hash equality and exact active FeatureRule equality.

## Privacy and aggregation

- Owner and Project scope hashes are used only for distinct-count evaluation.
- Neither Owner nor Project coordinates are copied into the output.
- Each output source is represented by a new digest over exact history/revision/entry/candidate/Profile coordinates.
- Duplicate Owner sources and cross-Owner Evidence replay are rejected, preventing one Owner from inflating diversity or sample weight.
- Raw media, text body, host path and credentials are not accepted or emitted.

The six R0 axes remain separate. For each axis the candidate records the minimum per-Owner delta, total sample count and contributing Owner count. Eligibility uses the minimum Owner weighted benefit, not an average that could hide one Owner's regression.

## Result states

- `READY_FOR_HUMAN_KNOWLEDGE_PACK_REVIEW`
- `INSUFFICIENT_OWNER_DIVERSITY`
- `INSUFFICIENT_PROJECT_DIVERSITY`
- `INSUFFICIENT_SAMPLES`
- `AXIS_REGRESSION`
- `NO_REPRODUCIBLE_BENEFIT`

Structural, lineage, privacy or semantic mismatches raise and fail closed rather than becoming an eligibility state.

## Authority boundary

Every candidate fixes the following to false:

- Knowledge Pack write and promotion;
- automatic promotion;
- runtime Profile apply;
- rollback execution;
- Release and external effect.

Human review, independent Critic, signature and latest-source revalidation remain required. `signature_required=true` does not implement signing or grant signing authority.

## Failure modes

| Failure | Result |
|---|---|
| R5 registry empty or malformed | reject |
| R1 history hash differs from registered lineage | reject |
| decision absent, REJECTED, or not active in Profile lineage | reject |
| supplied R0 Evidence hashes differ | reject |
| duplicate Owner or Evidence replay | reject |
| hypothesis/action/condition differ | reject |
| active FeatureRule absent or semantically differs | reject |
| Owner/Project/sample diversity below policy | explicit non-ready state |
| any Owner axis regresses beyond policy | `AXIS_REGRESSION` |
| weakest Owner benefit below policy | `NO_REPRODUCIBLE_BENEFIT` |

## Critic review

Finding: R1 deliberately persists only Evidence hashes, so R1/R5 histories alone cannot prove Project diversity.

Correction: the compiler requires the exact typed R0 Evidence rows, checks their hashes against the selected R1 decision, counts Project scopes in memory and emits no scope coordinate.

Finding: repeated sources from one Owner could falsely satisfy sample or Project thresholds.

Correction: exactly one source per distinct Owner is accepted, and Evidence hashes cannot replay across Owners.

Finding: averaging could hide a harmed Owner or regressed axis.

Correction: the candidate retains minimum per-Owner axis deltas and the minimum Owner weighted benefit. A configured regression is a separate blocking state.

Finding: “promotion candidate” could be mistaken for a signed/released Pack.

Correction: the module has no I/O/signing API; all write/promotion/apply/rollback/release flags are fixed false and separate Human/Critic/signature gates are true.

Finding: a hash-consistent payload could relabel an aggregate result state, and a reusable source digest could correlate the same source across different candidates.

Correction: candidate construction recomputes state from counts/metrics/policy, requires one coordinate and full metric contribution per Owner, and scopes each source digest to the candidate ID and feature key.

Residual Critical / High / Medium findings: 0 / 0 / 0.

## Verification

- focused R6 tests: 5 PASS
- deterministic source-order-independent compilation and exact verifier: PASS
- strict schema and byte-identical schema mirror: PASS
- distinct eligibility states and lineage/privacy negative tests: PASS
- broader TASK-029/TASK-019 regression: 80 PASS
- full Product regression: 3786 PASS / 6 SKIP / 0 FAIL

Judge: ACCEPT_IMPLEMENTATION_COMMIT_READY_PENDING_HOSTED_INTEGRATION.
