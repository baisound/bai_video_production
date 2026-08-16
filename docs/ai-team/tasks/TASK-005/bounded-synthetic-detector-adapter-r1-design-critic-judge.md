# TASK-005 R1A — Bounded Synthetic Detector Adapter

## Authority and binding

- Authorization: `BVP-AUTH-20260816-TASK005-BOUNDED-SYNTHETIC-ADAPTER-R1A-01`
- Base: `4908bb4380c19dbbfbe3cf166d42b22280825a6e`
- Branch: `codex/task-005-bounded-synthetic-adapter-r1`
- Scope: exact four files; dependency, schema, package-export and external-effect changes `0`
- Native H3: `PARKED`

## Design

The adapter is an immutable synthetic-only implementation of the R0
`SceneBoundaryDetectorAdapter` protocol. Construction binds one exact
`SceneSourceBinding`, one exact `DetectorProfile`, and an immutable tuple of
`DetectedSceneRange` rows. It checks only the R0 domain types and delegates
count, ordering, gap, overlap, tail coverage, source extent and row validation
to `build_scene_boundary_manifest`; no second validator or manifest compiler is
introduced.

`detect` succeeds only when every source and profile field is value-identical
to the construction binding. A changed Asset ID, source checksum, frame rate,
total frame count, profile ID, profile version or configuration digest rejects.
The return value is the already frozen tuple; no callback, runner, path, media
body, cache or mutable alias exists.

Security review narrowed all constructor inputs to exact R0 domain object types
and an exact built-in tuple. Arbitrary `Sequence` implementations and domain
subclasses are rejected before iteration, preventing an adapter-shaped input
from hiding callbacks or alternative equality semantics.

## Authority and compatibility boundary

This adapter supports deterministic contract tests only. It cannot read media,
discover or execute FFmpeg/ffprobe/OpenCV/PySceneDetect, choose a model or
Provider, make a Human decision, write Blueprint/Timeline state, or authorize
generation. R0 review-required/no-effect manifest flags remain authoritative.
TASK-004 and TASK-013 contracts are imported or modified `0`; Native H3 remains
independent and parked.

## Builder / Completeness Critic

- exact source/profile lineage is preserved across construction and detection;
- malformed, empty, gap, overlap, tail and max+1 proposals fail through R0;
- output identity and canonical manifest result are deterministic;
- R0 validation logic is reused rather than copied.

Result: `PASS`; residual Critical/High/Medium `0/0/0`.

## Security / Authority Critic

- the constructor surface contains only source, profile and proposal values;
- no path, raw bytes, callback, runner, filesystem, subprocess or network API exists;
- arbitrary sequences and subclass identity/equality overrides are rejected;
- the synthetic result cannot be promoted to detector accuracy, media-read,
  Human approval, downstream mutation or generation authority;
- mismatch and unknown type states fail closed.

Result: `PASS`; residual Critical/High/Medium `0/0/0`.

## Operations / Compatibility Critic

- Python 3.11–3.13 compatible standard-library implementation;
- new dependency, schema, package export, workflow and shared-file changes `0`;
- proposal count is bounded by the existing R0 maximum of 100,000;
- retained state is one immutable source/profile binding and one bounded tuple.

Result: `PASS`; residual Critical/High/Medium `0/0/0`.

## Verification and provisional Judge

Promotion requires focused R1A and R0 tests, deterministic/mismatch/bounds and
forbidden-surface negatives, compileall, exact four-file scope, `git diff
--check`, proportionate Windows/WSL2 full regression and terminal hosted checks.

Local verification result:

- focused R1A + R0 regression: `36 passed`;
- Windows full regression: `1309 passed, 1 skipped` (the existing non-Windows
  credential-vault contract skip);
- WSL2 full regression using the existing offline test environment: `1310 passed`;
- Windows and WSL2 compileall: `PASS`;
- dependency install/download, media read and external effect: `0`.

The independent Judge may return PASS only with unresolved Critic
Critical/High/Medium `0/0/0`, immutable R0 blobs, fresh base/head/Lock/overlap
closure and no external effect. Passing R1A closes only the synthetic adapter
test seam. A real detector/runtime remains a separate Gate.

Current pre-hosting result:
`PASS_LOCAL_READY_FOR_ATOMIC_COMMIT_AND_DRAFT_PR`.
