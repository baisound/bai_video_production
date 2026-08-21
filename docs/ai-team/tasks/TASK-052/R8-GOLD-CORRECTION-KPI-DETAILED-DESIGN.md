# TASK-052 R8 — Human Gold / Correction / KPI Closure

## Boundary

R8 provides a deterministic, side-effect-free dataset and evaluation contract.
It does not manufacture Human labels, read private media, run a detector, authorize
an accuracy claim or mutate canonical Knowledge/Timeline state.

The Owner workspace inventory contains only 16 Perk visual-training samples and no
5–10 match cross-domain Human Gold pilot. Real-media production accuracy therefore
remains `NOT_CONFIRMED`; this implementation makes the missing Evidence explicit
instead of substituting synthetic fixtures.

## Dataset manifest

Each manifest pins dataset revision, detector/model versions and canonically sorted
matches. Every match retains source/rights provenance, patch, HUD Profile, split,
real-media status and covered domains. A source group cannot cross TRAIN,
VALIDATION and TEST, preventing match/source leakage.

Pilot completeness requires 5–10 matches containing generator, chase, Survivor
state, hook, speaker, transcript and tactical-note labels. Recognition KPI coverage
on held-out TEST data additionally spans generator, chase, Survivor state, hook,
Perk, Killer, Map, Status Effect, object/scene and Add-on domains.

## KPI and fail-closed claim policy

Per-domain reports expose TP, FP, FN, TN, UNKNOWN, contradiction, invalid claims,
precision, recall, calibration error, replay stability and mean latency. A predicted
claim whose validator is not `VERIFIED` is counted as invalid. The report records
the exact manifest digest.

An accuracy result remains `NOT_CONFIRMED` unless all completeness, held-out,
real-media and validator conditions pass and an explicit production-accuracy claim
gate is supplied. Synthetic tests cannot authorize a production claim.

## Human feedback

Immutable corrections retain original/corrected label, Human reviewer, reason and
provenance and are emitted as improvement-candidate IDs. Rejected candidates retain
domain, candidate/provenance references and durable reason codes; report consumers
can query rejection counts by reason without reading private media bodies.

## Verification and remaining truth

- R8 + existing Event/HUD/Status Gold focused regression: `25 PASS`;
- TASK-049 DbD/Gold and TASK-052 affected regression: `291 PASS`;
- split leakage, incomplete pilots, non-real media and unvalidated claims fail closed;
- production accuracy from current Owner data: `NOT_CONFIRMED`;
- unresolved Critical/High findings: `0 / 0`.

Creation of the missing 5–10 match Human-labelled corpus requires actual Owner media
and Human labeling and cannot be synthesized by this implementation. R9 continues
with available packaged EXE, backup/restore, interaction and performance Evidence.
