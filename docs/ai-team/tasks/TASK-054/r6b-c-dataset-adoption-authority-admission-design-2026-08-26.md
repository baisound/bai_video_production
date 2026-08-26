# TASK-054 R6B-C Dataset Adoption Authority Admission Design

Date: `2026-08-26`

Status: `BOUND_FOR_IMPLEMENTATION`

Development depth: `DEV-3 HIGH ASSURANCE`

## Goal

Admit one separate Human Dataset-adoption authority against one exact R6B-B
`DATASET_ADOPTION_REVIEW_REQUIRED` preflight and compile one body-free,
one-shot Dataset adoption request proposal. This slice does not read or adopt a
Dataset, write a Dataset Store, authorize training, start training, evaluate a
model, promote a Binding, execute a Provider, or create any external effect.

## Canonical ownership

- R4A remains Dataset rights/provenance manifest admission owner.
- R6B-A remains read-only filesystem discovery owner.
- R6B-B remains Dataset Evidence selection/preflight owner.
- R6B-C owns only exact Human Authority admission, selected-coordinate crossing
  checks, validity/trust checks, one-shot Authority use, and a body-free request
  proposal.
- A later separately authorized executor must re-admit the request, reread the
  canonical manifest through R4A, recheck current rights and Dataset state, and
  own any actual Dataset Store mutation.
- Training remains a separate Human-Gated execution and is never implied by a
  Dataset adoption request.

No second Dataset Store, rights registry, training service, model registry,
Provider resolver, credential store or Product entrypoint is introduced.

## Input authority

`DatasetAdoptionAuthority` is an exact, checksum-protected, body-free record. It
binds:

- a safe authorization ID and a non-secret Human Authority Evidence digest;
- the exact R6B-B preflight digest;
- selected manifest ID/revision/rights-manifest digest;
- selected logical-path and observation digests;
- a UTC validity interval;
- fixed scope `DATASET_ADOPTION_REQUEST_ONLY`;
- exactly one request; and
- fixed state `ALLOWED_SINGLE_DATASET_ADOPTION_REQUEST`.

The Authority is Evidence, not a credential and not a Dataset/training effect.
An injected verifier must trust the Evidence digest. An injected atomic use
Store must claim the exact authorization digest once. Missing collaborators,
replay, stale time, checksum forgery or coordinate crossing fail closed.

## Output request

`DatasetAdoptionRequest` retains only body-free authority/preflight/selection
coordinates and creation time. Its invariants are:

- `dataset_adoption_requested=true`;
- `dataset_adoption_started=false`;
- `training_authorized=false`;
- `training_started=false`; and
- state `AUTHORIZED_PROPOSAL_NO_DATASET_ADOPTION_OR_TRAINING_EFFECT`.

Raw paths, manifest JSON, media, transcripts, narration, credentials and secret
values are outside both public records.

## Admission sequence

1. Require verifier and atomic use Store collaborators.
2. Exact-admit R6B-B preflight and R6B-C Authority.
3. Require learning-preparation status
   `DATASET_ADOPTION_REVIEW_REQUIRED`, an eligible candidate and the separate
   Dataset-adoption Gate marker.
4. Compare every selected identity/digest coordinate exactly.
5. Require current UTC time within `[not_before, expires_at)`.
6. Verify the non-secret Human Authority Evidence digest.
7. Construct the no-effect body-free request.
8. Atomically claim the Authority digest once; repeated use fails closed.
9. Return the request. No Dataset or training execution follows in this slice.

## Failure behavior

- confirmation-only, blocked, zero-eligible or forged preflight: reject;
- stale/crossed manifest, revision, rights, path, observation or preflight
  digest: reject before verifier/use Store;
- inactive Authority: reject before verifier/use Store;
- untrusted Authority Evidence: reject before use Store;
- missing use Store or repeated claim: reject without a request result;
- unknown fields, checksum drift, scope/state expansion, training flags or raw
  path injection: exact admission rejects;
- no fallback, retry, implicit reauthorization or authority widening exists.

## Allowed files

- `src/ai_video_production/dbd_reasoning_dataset_adoption_authority.py`
- canonical schema and packaged mirror
- `tests/test_task054_dbd_reasoning_dataset_adoption_authority.py`
- this design
- bounded TASK-054 checkpoint update

Must not modify R4A/R6B-A/R6B-B semantics, Dataset contents or stores, training,
evaluation, model/Binding lifecycle, Provider execution, credentials, shared
CHANGELOG/LOCK metadata, Release, Deploy or Production state.

## Acceptance

- exact Human Authority is preflight/selection/time/trust/checksum bound;
- one Authority produces at most one body-free request proposal;
- replay and every identity crossing fail closed;
- output cannot represent Dataset adoption started or training authority/effect;
- canonical schema and packaged mirror are byte-identical;
- focused R6B-C/R6B-B/R6B-A/R4A tests and relevant TASK-054 regression pass;
- unresolved Critical/High review findings are `0 / 0`.
