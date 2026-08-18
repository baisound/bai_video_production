# TASK-049 R10A — Critic Review

## Result

`PASS_WITH_REAL_MEDIA_HUMAN_GOLD_GATE`

## Findings

1. **Synthetic fixture presented as production accuracy:** blocked; dataset kind is explicit and reports never authorize a production accuracy claim.
2. **Unlabelled data called Gold:** blocked; every `HUMAN_GOLD` case requires `labeler_ref` provenance.
3. **Wrong class hidden inside binary metrics:** blocked; wrong asserted Event class contributes one FP and one FN.
4. **UNKNOWN behavior ignored:** blocked; expected-abstention cases and Unknown Detection Rate are first-class.
5. **Confidence score treated as calibration:** blocked; calibration error is measured separately from raw confidence.
6. **Timing quality reduced to float seconds:** blocked; range errors are measured from exact source frames.
7. **Partial prediction set silently scored:** blocked; prediction case IDs must exactly equal the dataset case set.
8. **Metric report confused with acceptance policy:** blocked by explicit `production_accuracy_claim_authorized=false`.

## R10B gate

Real DbD video and Human-labelled Gold cases are required before native detector accuracy can be measured. Production thresholds, if any, require explicit policy/Owner approval after measured evidence exists.
