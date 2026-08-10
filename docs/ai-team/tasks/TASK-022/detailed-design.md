# TASK-022 — Detailed Design

## 1. Boundary model

The service is a pure deterministic compiler. It does not inspect media, choose edits or write to Resolve. Inputs must already refer to canonical Assets admitted by TASK-003 and, when applicable, the exact whole-file normalization map emitted by TASK-004.

All ranges are `[start, end_exclusive)`. This removes inclusive-last-frame ambiguity and allows adjacent clips to meet without overlap.

## 2. Exact clocks

`FrameRate` remains numerator/denominator. Timeline duration is calculated with `Fraction`; Python float conversion is forbidden. The compiler applies:

- source→normalized start: `FLOOR`;
- source→normalized end-exclusive: `CEIL`;
- Timeline frame duration: `CEIL`;
- Timeline start: exact integer cursor plus explicit integer gap.

The conservative end rounding ensures a requested interval never loses source content because of rate conversion. It may expose at most the bounded rounding remainder represented by the final Timeline frame.

## 3. Affine normalization map

`AffineTimeMap` binds source and normalized starts/durations. It accepts timestamps only inside the closed map boundary for conversion, while consuming ranges as end-exclusive intervals. Forward and inverse mapping use exact integer rational arithmetic and caller-selected rounding.

A segment may use its source Asset directly, or bind both `normalized_asset_id` and `affine_map`. Supplying only one is invalid because it would make provenance and clock ownership ambiguous.

## 4. Edit segment

An `EditSegment` contains a stable placement ID, source Asset ID, end-exclusive source range, optional normalized binding, positive rational playback rate and non-negative frame gap before placement. The service validates Product Asset IDs before mapping.

## 5. Placement compilation

The compiler advances an integer frame cursor from `timeline_origin_frame`. For each segment it applies its gap, maps its clock range, divides mapped duration by playback rate, converts the result to a CEIL frame count and emits at least one frame. Each placement records original and mapped Asset/ranges plus exact playback rational.

`TimelineMappingPlan` rejects duplicate IDs, overlaps and out-of-order placements. Empty Plans are valid and have zero duration.

## 6. Deterministic serialization

Plan body uses canonical JSON ordering and receives `plan_sha256` calculated before the hash field is inserted. Re-serialization of the same Plan is byte-semantically stable. The hash detects Plan drift; it is not an authorization signature.

## 7. Integration route

- TASK-004 supplies normalization affine maps and canonical proxy Assets.
- TASK-006/007/024 supply subtitle/cut decisions as source ranges.
- TASK-013/014/TASK-027 supply generated or manually replaced canonical Assets.
- TASK-026 supplies audio placement decisions.
- TASK-010 consumes frame placements and owns Resolve mutation.

Replacing a TASK-027 Asset changes its slot binding, after which TASK-022 recompiles only the dependent placement Plan. Old Plans and Assets remain immutable Evidence.

## 8. Failure behavior

Invalid IDs, zero/negative ranges, unpaired normalization bindings, out-of-map timestamps, invalid speeds, negative gaps, duplicate IDs, overlaps and cross-drive/path concerns are rejected before any downstream side effect. The service has no filesystem or network side effects.
