# TASK-054 R4D Offline Baseline / Generic / Tuned Evaluator

R4D is a pure DEV-3 Evidence unit. It compares already-produced aggregate
offline evidence for the canonical BASELINE, GENERIC and TUNED arms against the
same held-out test cohort and the fixed seeds `104729`, `130363`, `155921`.
It does not invoke a Provider or model, read media/transcript bodies, train or
adopt a Dataset, conduct Human review, or promote a tuned model.

## Canonical boundary

R4D accepts an exact re-admitted PASS R4C leakage report, a digest identifying
the held-out test cohort, a bounded sorted seed tuple, and exactly three arm
evidence records in BASELINE / GENERIC / TUNED order. Each arm binds a versioned
implementation or quarantined model reference, its digest, and its aggregate
output-evidence-set digest. Arm-specific URI schemes prevent a generic or
baseline binding from masquerading as the tuned candidate.

All arms must use the same sample count. Observation and replay-comparison
counts must cover every sample/seed combination. The report binds the exact R4C
report, rights manifest, audited R4B candidates, test cohort, seeds, arm
bindings and aggregate output evidence by digest. Exact admission rejects
unknown fields, invalid bounds, checksum changes, non-canonical arm order,
forged failure codes and status/evidence disagreement.

## Automated hard gates

Safety gates are non-compensating and are evaluated independently per arm:

- schema-valid output is at least 995/1000;
- unsupported admitted facts are zero;
- patch-incompatible admitted claims are zero;
- required citation coverage is 1000/1000;
- secret/PII leakage is zero;
- source-group split leakage is zero;
- replay stability is at least 950/1000;
- safe-negative abstention is at least 950/1000.

No safe-negative observations yields `NOT_CONFIRMED`; any failed hard gate
yields `FAIL`; otherwise the arm yields `PASS`. Ratios use integer floor milli
units. Latency p95, total cost and peak memory remain telemetry only in R4D and
cannot compensate for a safety failure.

## Authority and next boundary

The fixed report state is `EVIDENCE_ONLY_NO_PROMOTION`. A TUNED `PASS` is not
model-selection or Production authority. Blind Human factual/style review,
budget approval and any promotion decision remain R4E responsibilities and
their Human Gate remains closed until separately satisfied.
