# TASK-098 A4-R2b Concrete Runtime Pre-mutation Review

- Date: `2026-09-22`
- Project / Task / Unit: `BAI VIDEO PRODUCTION / TASK-098 / A4-R2b`
- Development depth: `DEV-3 HIGH ASSURANCE`
- Starting HEAD: `b2c657472c91f1aa847cb2a66ee8aee5358816f4`
- Base/current-main identity: `28ba61e5f01047a716c681a3584be22500fe53fc`
- Branch: `codex/task-098-a4-review-workspace`
- Owner Human Gate: `APPROVED 2026-09-22` for bounded private-audio read, playback, waveform generation and native verification
- Result: `DESIGN_ACCEPTED / A4-R2B1_IMPLEMENTATION_ALLOCATED / A4-R2B2_PRIVATE_ASSET_ACCEPTANCE_DEPENDENCY_PENDING`

## Current state and responsibility split

The A4-R2a exact-hash request/reducer is complete at `b2c65747`. The current
Product Asset Registry contains zero Assets, so no exact canonical private WAV
is available for a truthful private-audio acceptance run. Owner approval does
not by itself authorize importing an arbitrary host path or mutating Product
state to manufacture that dependency.

A4-R2b is therefore divided without weakening the approved boundary:

- `A4-R2b1` implements the disabled-by-default concrete registry-bound runtime,
  deterministic fixture coverage and a bounded Windows-native synthetic WAV
  acceptance. It may create only isolated test state below pytest/OS temporary
  roots and may allocate the audio device only in the explicit native test.
- `A4-R2b2` retains the approved one-run private-audio acceptance. It becomes
  executable when an exact suitable WAV Asset exists in the canonical Product
  registry with matching TASK-041 source identity. It must not accept a host
  path from Shell, CLI or the user.

Neither unit owns a TASK-041 receipt, review completion, Human decision,
Asset/Candidate/Timeline mutation, Release, Deploy or Production Activation.

## A4-R2b1 design

The concrete Port is constructed explicitly from the canonical Product store,
`LogicalPathResolver` and a playback backend. It is never installed into the
default Product or Shell composition by this unit.

For each request it must:

1. obtain the Asset only by `source_asset_id` from the canonical store;
2. require AUDIO/BGM/SFX media, allowed registry rights, exact registry checksum
   agreement with the exact TASK-041 source content checksum, and exact Job
   scope for the Asset logical URI;
3. resolve the logical URI internally and reject non-Path, missing, non-regular
   or symlink sources before opening. The existing lexical resolver follows
   symlinks during canonicalization, so R2b1 adds one read-only resolver method
   which lstat-checks the configured root and every logical path component;
4. open read-only, pin the file handle, hash the same opened bytes, recheck file
   identity, then parse only uncompressed PCM WAV;
5. require 48 kHz and exact source duration, then decode only the requested
   half-open sample range under a fixed decoded-byte cap;
6. compute only a bounded peak-envelope point count process-locally, erase the
   derived list before return and expose no amplitude values;
7. build an in-memory range WAV only when audition was requested; and
8. own cancellation/stop cleanup. A backend disconnect or unbounded stop is
   `UNKNOWN_AFTER_DISCONNECT`, never success.

The A4-R2a internal request gains the exact source content checksum. That value
is part of the request hash but remains absent from every public projection.

## Allowed files

- `src/ai_video_production/task098_review_media_runtime_contract.py`
- `src/ai_video_production/task098_review_media_runtime_windows.py`
- `src/ai_video_production/paths.py`
- `tests/test_task098_review_media_runtime_contract.py`
- `tests/test_task098_review_media_runtime_windows.py`
- `tests/test_paths.py`
- bounded TASK-098 task/design/Evidence/current-state/task-index documentation

Existing Asset Registry, existing resolver behavior, TASK-041 contracts/stores, Shell/UI,
dependencies, installer/package, Product version and unrelated source/tests
must not change.

## Acceptance

- exact Asset/checksum/rights/job/logical-root/file identity is fail-closed;
- path is not accepted in request, Port method, public status or Shell;
- non-WAV, compressed WAV, non-48-kHz, duration drift, oversized range,
  checksum drift, symlink and registry identity drift are rejected;
- exact range decode and bounded waveform metadata are proven with fixtures;
- playback occurs only through an explicitly injected backend;
- Windows-native acceptance uses one short synthetic low-amplitude WAV inside a
  unique OS temporary directory and records device cleanup truthfully;
- cancel and disconnect do not become completion;
- private/user audio and existing Product data are not read or changed in R2b1;
- focused plus relevant A4/TASK-041 regression, diff review and durable Evidence
  pass before commit-ready state.

## Critic / Tester / Judge

- Critical: adding a host path or Asset import escape would bypass the canonical
  boundary. Rejected; exact Asset ID and internal logical resolution only.
- High: request lacked the content checksum needed to prove registry/source
  agreement. Corrected by adding an internal hash-bound checksum field.
- High: resolving then reopening by path could allow identity substitution.
  Corrected by hashing/decoding through one pinned read-only handle plus identity
  recheck, and by lstat-checking every logical path component before and after
  the read through a new resolver API.
- High: a synchronous Windows playback call could hide cancellation failure.
  Corrected by an owned worker, bounded join, explicit stop and unknown state on
  disconnect/unbounded cleanup.
- High: waveform bodies could escape through result/Evidence. Corrected by a
  process-local peak envelope and point-count-only observation.
- Medium: unrestricted ranges could duplicate large private bodies in memory.
  Corrected by a fixed decoded-byte cap before frame read.
- Medium: synthetic native success could be mislabeled private-audio acceptance.
  Corrected by retaining R2b2 as dependency-pending.
- Final design findings: `Critical 0 / High 0 / Medium 0 / Low 0`.
- Tester/Judge: `PASS / ACCEPT A4-R2B1 / RETAIN A4-R2B2 DEPENDENCY`.
