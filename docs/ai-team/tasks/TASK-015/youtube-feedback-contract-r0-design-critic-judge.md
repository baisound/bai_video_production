# TASK-015 R0 YouTube Feedback — Design / Critic / Judge

## Decision

`IMPLEMENT_CREDENTIAL_FREE_AGGREGATE_FEEDBACK_CONTRACT`

## Design

- `YouTubePublicationBinding` preserves public video ID separately from channel identity digest and exact Asset/Edit Plan/render receipts.
- `FeedbackProfile` serializes canonical required/optional metric sets. Absence never means zero and UNKNOWN never means missing.
- Six aggregate metric kinds have one exact unit and bounded integer domain. Percentages are milli-percent integers; float input is rejected by the integer validator.
- `AnalyticsObservation` preserves manifest/row/SHA/current-valid provenance for each metric.
- Snapshot state precedence is stale/revoked, UNKNOWN, missing required, then complete. Every non-complete population remains serialized.
- TASK-008 is reused through its exact scoring-manifest SHA coordinate; this unit does not duplicate or mutate normalization/scoring logic.
- Output is `REVIEW_REQUIRED`; automatic tuning, Edit Plan mutation, publication mutation and all external effects remain false.

## Negative matrix

- malformed video/Asset/SHA/row coordinates
- analytics window before publication, empty or greater than 366 days
- duplicate or undeclared metric
- metric/unit mismatch and milli-percent cap+1
- unsorted/duplicate/overlapping profile sets
- required metric absence treated zero/current
- UNKNOWN or stale/revoked observation promoted complete
- nested profile digest or outer snapshot tamper
- audience-level row or Credential/API/media/filesystem/network/subprocess surface
- feedback snapshot promoted TASK-019 tuning, TASK-008 profile, Edit Plan, Timeline or publication authority

## Builder / Completeness Critic

Finding: deriving ratios inside this contract would introduce denominator/rounding policy and duplicate an analytics producer.

Correction: R0 preserves typed producer observations exactly; each ratio uses an explicit milli-percent unit and provenance row. No derived metric is fabricated.

Residual C/H/M: `0/0/0`.

## Security / Authority Critic

Finding: a YouTube video ID could be mistaken for account authority or justify API/Credential access.

Correction: channel identity remains a non-reversible digest, inputs are aggregate rows only, and the module has no credential, API, network or audience-row surface.

Residual C/H/M: `0/0/0`.

## Operations / Compatibility Critic

Finding: unordered observations and floating point percentages could make receipts unstable across platforms.

Correction: metric rows and profile sets are canonically sorted; all values are bounded integers and canonical JSON/SHA is reused.

Residual C/H/M: `0/0/0`.

## Independent Judge

- TASK-008 coordinate binding / duplicate scoring logic zero: PASS
- publication/window/profile/metric/provenance closure: PASS
- missing/UNKNOWN/stale/revoked partitions: PASS
- privacy and credential/API/no-effect boundary: PASS
- deterministic hash/schema mirror and negative matrix: PASS
- focused/full regression, compileall, release metadata and hosted checks: PENDING EVIDENCE
- residual C/H/M: `0/0/0`

`JUDGE=PASS_LOCAL_PENDING_HOSTED_EVIDENCE`
