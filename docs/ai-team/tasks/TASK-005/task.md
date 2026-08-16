# TASK-005 — Scene Boundary

## Current unit

`Scene Boundary Contract Foundation R0` adds a deterministic, review-only
manifest for proposed scene boundaries. The unit binds a canonical source
Asset checksum, reduced rational frame rate, total frame count, detector
profile/version/configuration digest, and an ordered complete partition of the
source into half-open frame ranges.

## Responsibility boundary

TASK-005 owns media Scene Boundary analysis contracts. It does not replace:

- TASK-013 scene-compatible reference feasibility or generation request compilation;
- TASK-037 Scene Asset Slot/Candidate state;
- TASK-042 Production Blueprint V2, FrameIntent, or world-lock contracts;
- TASK-036 read-only Scene/Human review screens;
- TASK-044 NLE timeline/edit operations.

R0 provides only the pure contract, adapter protocol, and synthetic fixtures.
It does not read media, select or execute a detector, invoke FFmpeg/OpenCV or a
Provider, mutate Blueprint/Timeline state, apply a cut, authorize generation,
or complete TASK-005 detector runtime.

## R0 acceptance

- immutable manifest/domain objects;
- exact Asset/checksum/frame/profile binding;
- canonical contiguous IDs and ordered gapless full-frame coverage;
- canonical JSON and non-self SHA-256 verification;
- public/package JSON Schema byte parity;
- review-required and no-effect flags fixed fail-closed;
- focused, full, and hosted regression with unresolved Critic C/H/M `0/0/0`.

Native H3 recovery remains parked and is not a TASK-005 dependency or effect.

## R1A bounded synthetic adapter

`BoundedSyntheticSceneBoundaryDetectorAdapter` is the first concrete adapter
for contract and integration tests. It is immutable and binds exactly one R0
source, detector profile, and prevalidated in-memory proposal tuple. Detection
rejects any source/profile mismatch and delegates all proposal count, range,
coverage, manifest, and hash rules to the existing R0 compiler.

R1A is explicitly synthetic-only. It accepts no path, raw bytes, callback,
runner, filesystem handle, Provider, model, or native-runtime input. It neither
reads media nor proves detector accuracy. FFmpeg/OpenCV/PySceneDetect selection,
real-media analysis, Human review, downstream editing, and Native H3 remain
separate parked Gates.
