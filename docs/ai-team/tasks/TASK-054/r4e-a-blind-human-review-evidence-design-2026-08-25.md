# TASK-054 R4E-A Blind Human Review Evidence

R4E-A is the first bounded DEV-3 slice of R4E. It defines body-free,
exactly-bound evidence for a reviewer to compare three commentary candidates
without seeing whether a candidate is BASELINE, GENERIC or TUNED. It does not
render candidate text, authenticate a Human, reveal model identity before
submission, aggregate a winner, propose promotion, or promote/activate a model.

## Inputs and canonical ownership

- exact re-admitted R4D offline evaluation report;
- a PASS TUNED automated gate in that report;
- opaque held-out sample references and candidate-output digests;
- an externally issued, one-shot Human confirmation bound to one reviewer,
  review pack, sample and submission digest.

R4D owns automated evaluation. Existing R2 Human review continues to own
approval/revision of one commentary Candidate and is not reused as comparative
model-ranking evidence. R4E-A owns only the comparative blind-review records.

## Two-object blind boundary

The UI-facing `BlindReviewPresentation` contains:

- exact R4D report digest and test-sample-set digest;
- one opaque pack reference and digest;
- sorted opaque sample references;
- for each sample, labels `A`, `B`, `C` with only candidate-output digests;
- no arm, binding, model, Provider, prompt, transcript or commentary body.

The separately retained `BlindReviewRevealManifest` contains the exact mapping
from each sample label to one of BASELINE / GENERIC / TUNED and binds each
mapping to the R4D arm binding digest and arm output-evidence-set digest. It must
not be supplied to the reviewer-facing path before submission. Presentation and
reveal manifest share the same pack digest and complete sample set.

Label assignment is a permutation per sample. Each sample must map all three
arms exactly once; this avoids a fixed label becoming a model identity. Pack
construction is deterministic from caller-supplied sealed mappings and performs
no random generation or I/O.

## Submission contract

One `BlindHumanReviewSubmission` binds:

- pack digest, R4D report digest and one opaque sample reference;
- pseudonymous reviewer reference `reviewer://sha256/<digest>`;
- the three candidate-output digests exactly as presented;
- a factual-acceptability boolean for A/B/C;
- 1..5 integer scores for uncertainty handling, usefulness, timing,
  naturalness and density for A/B/C;
- preference `A / B / C / ALL_REJECTED`;
- sorted stable reason codes, reviewed-at UTC timestamp;
- one-shot external Human confirmation reference and digest;
- canonical submission digest.

The submission contains labels only. Arm, binding and model identity are
forbidden. A submission is admitted only against the exact presentation;
candidate substitution, sample crossing, pack drift, duplicate labels,
non-Human/missing confirmation, malformed score, secret-like reference and
checksum changes fail closed.

## R4E-B handoff

R4E-B will separately accept an exact R4E-A presentation, reveal manifest and a
complete set of admitted submissions. It will enforce reviewer/sample coverage,
unique one-shot confirmations, reveal identities only after admission, compute
factual non-regression, style preference and inter-reviewer agreement, and emit
only a promotion *candidate* report. Actual Human review collection, budget
approval, binding `APPROVED`, default-route activation, Product activation,
release and deployment remain separate Human Gates.

## Bounds and acceptance

- 1..1000 samples per pack;
- exactly three labels per sample and exactly three arm mappings per sample;
- at most 16 reason codes per submission;
- canonical JSON size ceilings for every record;
- exact Schema plus Product-resource mirror;
- deterministic hash, exact re-admission, negative crossing/tamper tests;
- no filesystem, network, Provider/model, media, Dataset, training, Timeline,
  TTS, Resolve, release, deployment or promotion side effect.
