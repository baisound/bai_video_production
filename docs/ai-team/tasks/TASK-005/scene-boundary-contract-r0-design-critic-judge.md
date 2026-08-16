# TASK-005 Scene Boundary Contract R0 — Design, Critic, and Judge

## Authority and start binding

- Authorization: `BVP-AUTH-20260816-TASK005-SCENE-BOUNDARY-CONTRACT-R0-01`
- Start base: `79ec54eeea9c14ddde488f861547acf541d9382b`
- Branch: `codex/task-005-scene-boundary-contract-r0`
- Open PR / candidate branch / exact-path overlap at start: `0 / 0 / 0`
- Active implementation locks: TASK-046/P-VS-3B and TASK-047/DEV10; exact-path overlap `0`
- Native H3: `PARKED`

## Design

The contract accepts only already-observed in-memory `DetectedSceneRange`
values. `SceneBoundaryDetectorAdapter` is a structural protocol, not a
runtime implementation. The compiler assigns canonical contiguous scene IDs
and constructs an immutable manifest only when the ranges form an ordered,
gapless, non-overlapping, complete partition from frame zero through the exact
bound source frame count.

Source identity is a canonical TASK-003 Asset ID plus content SHA-256. Frame
rate is a reduced positive rational, avoiding float/timebase ambiguity.
Detector identity is a stable profile ID, semantic version, and canonical
configuration digest. Confidence is bounded integer milli-units and Evidence
codes are unique, sorted symbolic values. The manifest digest covers the full
canonical JSON body and excludes only its own digest field.

All rows remain `PROPOSED_FOR_REVIEW`; the manifest is `REVIEW_REQUIRED` and
fixes media-read, auto-apply, generation, and timeline-mutation authority to
false. Reconstruction of a digest or structural validity does not prove
semantic detector accuracy or Human approval.

## Non-duplication and effect boundary

No REF-A/B/C implementation is copied. The module imports none of the
TASK-013 feasibility, TASK-037 control, TASK-042 Blueprint, TASK-036 UI, or
TASK-044 timeline modules. It contains no filesystem writer, media reader,
subprocess, network, Provider, model, native-generation, Resolve, or release
surface.

## Builder / Completeness Critic

Review points:

- source frames are covered exact once with no gap, overlap, reorder, or tail omission;
- canonical IDs, reduced timebase, configuration digest, and manifest digest are deterministic;
- public and packaged schemas are byte-identical and reject aliases/extra fields;
- the adapter boundary does not silently become a detector runtime;
- existing Scene/Visual contracts remain authoritative and unmodified.

Corrections applied during review:

- detector configuration input now rejects non-JSON values, NaN/Infinity, and
  canonical payloads larger than 1 MiB before hashing;
- Python validators now match JSON Schema exact-integer semantics and the
  Evidence-code maximum of 64.

Result: `PASS`; residual Critical/High/Medium `0/0/0`.

## Security / Authority Critic

Review points:

- names or paths cannot substitute for canonical Asset ID/content checksum;
- digest validity does not grant media-read, Human decision, cut, generation, or timeline authority;
- no Provider, credential, paid, network, model, media, native H3, Resolve, release, or deploy effect exists;
- malformed/unknown range, checksum, frame rate, config, or Evidence state fails closed.

Result: `PASS`; residual Critical/High/Medium `0/0/0`.

## Operations / Compatibility Critic

Review points:

- Python 3.11–3.13 and Windows/Ubuntu CI compatibility;
- no new dependency, CLI, workflow, Registry, roadmap, CHANGELOG, or package export;
- exact six-file diff and zero overlap with Developer2 Audio/Narration/OBS work;
- schema package discovery works without `__init__.py` mutation.

Result: `PASS`; residual Critical/High/Medium `0/0/0`.

## Validation evidence

- Focused TASK-005 contract/schema/negative tests: `20 passed`.
- Public/package schema SHA-256 and byte parity: `PASS`.
- Python compileall: `PASS`.
- Windows full regression: `1293 passed, 1 skipped` (the existing
  non-Windows credential-vault contract skip).
- Ubuntu/WSL2 full regression using the existing offline test runtime:
  `1294 passed`.
- Dependency install/download/network/native/media/provider effect: `0`.
- Changed path set: exact six authorized new files.

## Independent Judge

Promotion requires focused tests, schema mirror/meta-validation, compileall,
proportionate full regression, `git diff --check`, exact six-file scope,
hosted terminal checks, fresh base/lock/overlap re-read, and Critic residual
Critical/High/Medium `0/0/0`.

Current pre-hosting result: `PASS_LOCAL_READY_FOR_ATOMIC_COMMIT_AND_DRAFT_PR`.
Final merge remains conditional on hosted terminal checks and fresh
base/head/files/lock/overlap read-back.

Passing this R0 closes only `TASK005_SCENE_BOUNDARY_CONTRACT_FOUNDATION`.
Detector runtime, real media analysis, Human acceptance, downstream editing,
native generation, and overall TASK-005 completion remain separate gates.
