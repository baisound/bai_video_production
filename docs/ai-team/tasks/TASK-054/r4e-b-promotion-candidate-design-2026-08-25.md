# TASK-054 R4E-B Blind Review Aggregation / Promotion Candidate

R4E-B is a pure DEV-3 aggregation unit over already-collected R4E-A evidence.
It does not show review content, collect a Human decision, execute a model,
approve a binding, choose a default route, or promote/activate anything.

## Exact inputs

- exact re-admitted PASS-TUNED R4D report;
- exact R4E-A blind presentation and sealed reveal manifest;
- a sorted expected reviewer cohort of 2..20 pseudonymous reviewer refs;
- one exact R4E-A submission plus unexpired external Human Authority Binding for
  every sample/reviewer coordinate.

All submissions are admitted against the blind presentation before the reveal
manifest is admitted. The aggregator then reveals labels internally. It rejects
missing/duplicate sample-reviewer coordinates, reviewers outside the expected
cohort, duplicate confirmation refs/digests, presentation/reveal/R4D drift and
any candidate-output crossing.

## Deterministic metrics

For BASELINE, GENERIC and TUNED, the report records:

- factual acceptable count and milli rate;
- preference count (`ALL_REJECTED` is not assigned to an arm);
- aggregate style score milli over uncertainty handling, usefulness, timing,
  naturalness and density;
- observation count.

Per-sample inter-reviewer preference agreement is calculated as agreeing
reviewer pairs divided by all reviewer pairs, then aggregated in floor milli.
At least 500/1000 agreement is required to claim that a preference comparison is
confirmed; lower agreement yields `NOT_CONFIRMED`, never an inferred winner.

## Non-compensating decision

`READY_FOR_OWNER_REVIEW` requires all of:

- TUNED R4D hard gate is PASS;
- complete exact reviewer/sample coverage;
- agreement at least 500/1000;
- TUNED factual acceptability is not below BASELINE;
- TUNED has more direct preferences than BASELINE;
- TUNED aggregate style score is above BASELINE.

Factual regression or absent style improvement yields `NOT_ELIGIBLE`.
Insufficient agreement yields `NOT_CONFIRMED`. Latency/cost/resource telemetry
remains in R4D and cannot compensate for any Human or safety failure.

## Authority

The output state is fixed to
`PROMOTION_CANDIDATE_ONLY_OWNER_DECISION_REQUIRED`. READY is a body-free report
for later Owner review, not approval. Budget acceptance, model/binding
`APPROVED`, default-route activation, Product activation, Timeline/TTS use,
release and deploy each retain their separate Human Gate.
