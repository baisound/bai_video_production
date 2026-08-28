# TASK-054 R6B-D Dataset Adoption Execution Preflight Design

Date: `2026-08-27`

Status: `BOUND_FOR_IMPLEMENTATION`

Development depth: `DEV-3 HIGH ASSURANCE`

## Goal

Consume one exact R6B-C body-free Dataset adoption request only after a second,
separate Human execution Authority has been admitted, reread and re-admit the
current R4A rights manifest, verify that the selected canonical Dataset Store
can satisfy the required safety floor, and compile one body-free commit plan.

This slice performs no Dataset Store mutation. It does not authorize or start
Dataset adoption, training, model/runtime acquisition, evaluation, Binding
promotion, Provider execution, paid work, Release, Deploy or Production.

## Canonical ownership

- R4A remains the only rights/provenance manifest admission owner.
- R6B-A remains the read-only discovery owner.
- R6B-B remains selection/preflight owner.
- R6B-C remains request-authority admission and one-shot request proposal owner.
- R6B-D owns execution-Authority admission, current-manifest reread crossing
  checks, Store capability preflight and body-free commit-plan compilation.
- A later separately authorized executor owns any actual atomic Store commit and
  authoritative read-back. R6B-D has no Store mutation method.
- Training remains a later separately authorized executor.

No parallel filesystem layout, hidden Dataset Store, training service, model
Registry, Provider resolver or Product entrypoint is introduced.

## Separate execution Authority

`DatasetAdoptionExecutionAuthority` binds:

- one non-secret Human Authority Evidence digest;
- the exact R6B-C request digest and all selected Dataset coordinates;
- one exact canonical Store ID and expected prior Store digest;
- a UTC validity interval;
- fixed scope `DATASET_ADOPTION_READ_ONLY_PREFLIGHT`; and
- fixed state `ALLOWED_READ_ONLY_DATASET_ADOPTION_PREFLIGHT`.

The R6B-C request Authority cannot be reused as execution-preflight Authority.
An injected verifier must trust the exact Evidence-digest-to-authorization-
digest binding. Authority verification occurs before any current manifest body
is read. Preflight is deterministic and read-only; it does not consume the
Authority. A later commit executor must consume the Evidence digest in the same
atomic transaction as the Store mutation.

## Store capability floor

Before manifest reread, an injected read-only Store capability reader must
report the exact authorized Store ID and all of the following fixed capabilities:

- encrypted at rest;
- atomic compare-and-swap against the authorized expected Store digest;
- authoritative post-commit read-back;
- append-only Dataset revisions; and
- one-shot execution Authority consumption at commit time.

A missing or weaker capability fails closed before manifest read. Capability
inspection cannot mutate or initialize the Store.
The read-only capability observation also includes the current Store head digest,
which must exactly equal the Authority's expected prior Store digest before the
plan can become ready.

## Current manifest and plan projection

The injected manifest reader receives only manifest ID and revision. It returns
the exact current R4A record plus the body-free logical-path and observation
digests. R6B-D exact-admits the record through R4A and requires every coordinate
and checksum to match the R6B-C request.

Only entries still classified `ELIGIBLE_CANDIDATE` are projected into the plan.
The public plan retains only candidate/lineage/Human-review digests and
Match/source-group/split coordinates. It does not retain raw paths, manifest
bodies, media, transcripts, narration, prompts, credentials or Dataset content.
At least one eligible membership is required. Membership IDs remain sorted and
source-group split isolation remains inherited from R4A admission.

The plan is fixed to:

- `dataset_adoption_requested=true`;
- `dataset_adoption_started=false`;
- `dataset_store_mutated=false`;
- `training_authorized=false`;
- `training_started=false`; and
- `READY_FOR_SEPARATE_DATASET_ADOPTION_COMMIT_AUTHORITY`.

## Admission sequence

1. Exact-admit R6B-C request and R6B-D preflight Authority.
2. Reject coordinate, Store, time or scope crossing before verifier/reader.
3. Verify Human Authority Evidence before manifest body read.
4. Reject an incapable Store before manifest body read.
5. Reread and exact-admit current R4A manifest.
6. Reject location/observation/identity/checksum drift and zero eligible rows.
7. Build and return the canonical body-free commit plan.
8. Perform no Authority consumption, Store mutation or training.

There is no fallback, implicit reauthorization, automatic retry, Dataset commit,
training dispatch or model activation.

## Allowed files

- `src/ai_video_production/dbd_reasoning_dataset_adoption_preflight.py`
- canonical schema and packaged mirror
- `tests/test_task054_dbd_reasoning_dataset_adoption_preflight.py`
- this design
- bounded TASK-054 checkpoint update

Must not modify R4A/R6B-A/R6B-B/R6B-C semantics, real Dataset bodies, Dataset
Store files, training/evaluation/model/Binding/Provider behavior, credentials,
shared CHANGELOG/LOCK metadata, Release, Deploy or Production state.

## Acceptance

- R6B-C request and separate preflight Authority are exact and crossed fail
  closed before any body read;
- only a trusted active exact Authority can reach manifest reread;
- Store encryption/CAS/read-back/append-only/one-shot capabilities are mandatory;
- the current R4A record is reread, exact-admitted and coordinate bound;
- only current eligible memberships enter one deterministic body-free plan;
- repeated exact input produces the same plan body apart from caller-bound plan
  identity/time, without consuming or widening Authority;
- output cannot represent Dataset Store mutation, training authority or start;
- canonical schema and packaged mirror are byte-identical;
- focused R6B-D/R6B-C/R4A tests and relevant TASK-054 regression pass;
- unresolved Critical/High findings are `0 / 0`.
