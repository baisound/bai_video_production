# TASK-054 R6B-B Dataset Evidence Selection Preflight Design

Date: 2026-08-26
Profile: DEV-3 HIGH ASSURANCE
Status: IMPLEMENTATION CHECKPOINT

## Goal

Bridge the body-free R6B-A discovery report to a bounded Operator selection
preflight without adopting a Dataset or authorizing training. The Operator may
choose one exact admitted manifest revision for either confirmation-only review
or learning preparation.

## Canonical boundaries

- R6B-A remains the only filesystem discovery owner.
- R4A remains the rights/provenance manifest admission owner.
- This unit consumes only an exact admitted R6B-A report.
- This unit does not reread manifest JSON, media, transcript or narration bodies.
- This unit does not create a Dataset revision, training job or model artifact.
- R7 Operator UI may render this contract later but is not a dependency of this
  Atomic Unit and remains isolated on PR #329.
- BAI Development OS is not a runtime dependency.

## Modes and outcomes

CONFIRMATION_ONLY:

1. no selection returns SELECTION_REQUIRED;
2. an exact selection returns EVIDENCE_REVIEW_READY;
3. the result remains evidence-only and does not expose learning controls.

LEARNING_PREPARATION:

1. no selection returns SELECTION_REQUIRED;
2. a selected manifest with zero eligible candidates returns
   BLOCKED_NO_ELIGIBLE_CANDIDATE;
3. a selected manifest with at least one eligible candidate returns
   DATASET_ADOPTION_REVIEW_REQUIRED;
4. the result requests a separate Human Dataset adoption Gate only. It does not
   satisfy or execute that Gate.

Missing or invalid discovery reports return BLOCKED_DISCOVERY. Supplying a
selection against a blocked report, a partial identity, stale revision, crossed
manifest digest or absent identity fails closed.

## Body-free output

The preflight binds:

- exact discovery report checksum;
- exact discovery observation timestamp;
- preflight creation time at or after the bound discovery observation;
- logical-path digest and observation digest from the selected discovery item;
- manifest id, positive revision and rights-manifest checksum;
- aggregate disposition and split counts;
- mode, stable status/detail code and immutable preflight checksum.

It never returns a raw path, manifest body, media, transcript, narration,
credential or private source reference.

## Authority floor

The following fields are schema/runtime constants:

- dataset_adoption_authorized=false
- training_authorized=false
- state=PREFLIGHT_ONLY_NO_DATASET_ADOPTION_OR_TRAINING_AUTHORITY

Even DATASET_ADOPTION_REVIEW_REQUIRED only identifies the next Human Gate.
Aggregate counts cannot prove eligible rows exist in a particular split, so the
preflight never claims training readiness.

## Failure modes

- noncanonical/tampered R6B-A report: reject during re-admission;
- partial selection: reject;
- stale/crossed selection: reject;
- invalid timestamp/hash/id/counts: reject;
- preflight creation before its bound discovery observation: reject;
- aggregate count mismatch: reject;
- forged authority/state/checksum: reject;
- no evidence or invalid evidence: stable blocked report;
- no eligible candidate: stable blocked learning-preparation report.

## Operator mapping

A later UI adapter should use the following fixed Japanese intent without
changing authority:

- CONFIRMATION_ONLY: Dataset Evidence review only; no learning;
- LEARNING_PREPARATION: prepare a request for Dataset adoption review;
- SELECTION_REQUIRED: choose one admitted Dataset revision;
- BLOCKED_DISCOVERY: resolve discovery Evidence first;
- DATASET_ADOPTION_REVIEW_REQUIRED: show a Human Gate card, not a training
  execution button.

## Acceptance

- exact R6B-A report re-admission;
- explicit single-revision selection;
- deterministic mode/status transitions;
- body-free checksum-bound output;
- Dataset adoption/training authority always false;
- runtime admission and JSON Schema reject tampering;
- canonical schema and packaged mirror are byte-identical;
- focused positive/negative/schema tests pass;
- no native, private-data, Provider, paid, Release, Deploy or Production effect.
