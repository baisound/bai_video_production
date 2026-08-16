# TASK-025 R0 Premiere FCP7 XML Adapter — Design / Critic / Judge

## Decision

`IMPLEMENT_DETERMINISTIC_SINGLE_VIDEO_TRACK_XMEML_V5_ADAPTER`

## Design

- TASK-022 remains the sole mapping authority; the adapter consumes real `TimelineMappingPlan` and does not reselect clips.
- Closed FCP7 rate mapping covers integer and 1000/1001 24/30/60 families plus 25/50.
- R0 admits timeline origin zero, one video track and exact 1x playback. Unsupported retime is rejected rather than silently flattened.
- Each mapped Asset has exact SHA, logical name, private `file://localhost` URI, frame rate and duration binding.
- Binding Asset set equals mapped Asset set exactly; source in/out must be contained and duration must equal the TASK-022 placement frame range.
- XML bytes are canonical one-line ElementTree serialization with fixed declaration/DOCTYPE/order/IDs.
- Public receipt binds the URI by digest and never exposes its value. XML bytes remain private because FCP7 needs `pathurl`.
- Compilation performs no read/write/import/application operation and grants no external mutation authority.

## Negative matrix

- unsupported or mismatched Timeline/sequence/media rate
- non-zero origin or retimed placement
- missing, extra or duplicate Asset binding
- mapped source range outside media duration
- unsafe placement identity
- URI scheme, traversal, encoded separator/parent, query, fragment or backslash
- XML byte/manual receipt tamper
- URI leaked into public receipt
- XML success promoted Premiere import, Asset/Timeline mutation or Golden Fixture PASS

## Builder / Completeness Critic

Finding: attempting audio, subtitle and retime support in the first slice would create several unverified FCP7 semantics at once.

Correction: R0 closes the smallest importable video-only subset and rejects every unsupported dimension explicitly. Later slices need their own fixtures and import Evidence.

Residual C/H/M: `0/0/0`.

## Security / Authority Critic

Finding: FCP7 `pathurl` can disclose a private host path or smuggle traversal/query data.

Correction: strict contained file URI validation, encoded separator/parent rejection and public receipt digest projection keep private values out of public Evidence.

Residual C/H/M: `0/0/0`.

## Operations / Compatibility Critic

Finding: arbitrary rational rates cannot be losslessly represented by FCP7 `timebase + ntsc`.

Correction: a closed exact matrix rejects unrepresentable rates and golden tests cover every accepted pair.

Residual C/H/M: `0/0/0`.

## Independent Judge

- TASK-022 mapping reuse and duplicate edit selection zero: PASS
- canonical XML/golden fixture/rate matrix: PASS
- Asset/URI/privacy/no-effect closure: PASS
- unsupported behavior fail-closed: PASS
- focused/full regression and hosted checks: PENDING EVIDENCE
- actual Premiere import Golden Fixture: SEPARATE GATE / NOT CLAIMED
- residual C/H/M: `0/0/0`

`JUDGE=PASS_LOCAL_PENDING_HOSTED_EVIDENCE`
