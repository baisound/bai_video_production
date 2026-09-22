# TASK-098 A4-R2b1 Concrete Runtime and Native Evidence R01

- Recorded: `2026-09-22T17:02:41+09:00`
- Project / Task / Atomic Unit: `BAI VIDEO PRODUCTION / TASK-098 / A4-R2b1`
- Run identity: `a4-r2b1-concrete-runtime-native-20260922-r01`
- Development depth: `DEV-3 HIGH ASSURANCE`
- Branch: `codex/task-098-a4-review-workspace`
- Starting HEAD: `b2c657472c91f1aa847cb2a66ee8aee5358816f4`
- Base/current-main identity: `28ba61e5f01047a716c681a3584be22500fe53fc`
- Owner Human Gate: `APPROVED 2026-09-22`
- Result: `PASS / COMMIT_READY / PRIVATE_ASSET_ACCEPTANCE_NOT_EXECUTED`

## Implemented boundary

- A4-R2a request now binds the exact source content checksum inside its request hash while every public projection remains digest-free.
- Concrete Port loads only the exact Asset ID through the canonical store and resolves only the registry logical URI.
- A new read-only resolver method rejects symlink roots/components, missing nodes and non-regular files without changing existing resolver behavior.
- The Port requires registry/source checksum agreement, allowed rights, exact Job scope, a pinned regular file identity, checksum before and after decode, uncompressed 48 kHz PCM and exact source duration.
- Only the requested half-open range is decoded under a fixed byte cap. Waveform peaks remain process-local, are zeroed before return and expose only point count.
- Windows playback receives only an in-memory bounded range WAV. Port-owned cancel/stop cleanup maps unknown cleanup to `UNKNOWN_AFTER_DISCONNECT`, never success.
- No Shell/UI/default Product composition, TASK-041 receipt, completion, persistence or Human decision was added.

## Review findings

- Initial focused run: `25 PASS / 5 FAIL`; test Job ID length and `Path` subclass acceptance were corrected.
- High: existing resolver canonicalization hid an in-root symlink component from the caller. Corrected with component-by-component lstat verification before and after read.
- High: cancel racing with playback completion and cleanup failure needed explicit terminal truth. Corrected with Port-owned cleanup plus concurrent cancel/disconnect tests.
- Medium: direct request construction did not independently validate Product Asset ID. Corrected.
- Medium: content could change after the initial hash, and source hashing had no absolute size bound. Corrected with a post-decode same-handle hash and fixed source-size cap.
- Final unresolved findings: `Critical 0 / High 0 / Medium 0 / Low 0`.

## Verification

- Final focused fake/boundary suite: `32 PASS / 1 Windows-native deselected`.
- Final A4/TASK-041/LogicalPathResolver integration regression: `94 PASS / 1 Windows-native deselected` in `6.67s`.
- Windows-native exact test: `1 PASS` in `0.59s`.
- Native test used a short low-amplitude synthetic WAV, isolated canonical store and Asset root below a unique OS temporary run directory.
- Native output root was not a drive root/direct child; `7` run items were observed and the exact run directory was removed after identity revalidation. Final residual count: `0`.
- `git diff --check`: `PASS`.
- Source/test public-secret/private-path scan: `PASS`; only pre-existing synthetic Windows canonicalization literals in `tests/test_paths.py` matched.

## Effects, residuals and next action

- Existing Product Asset Registry inspection: `0 Assets / 0 audio Assets`; read-only.
- User/private audio read: `NOT_EXECUTED`.
- Existing Product state mutation: `NONE`.
- Audio-device allocation/playback: `EXECUTED ONCE / SYNTHETIC BOUNDED TEST / PASS`.
- Waveform generation: `EXECUTED / SYNTHETIC / PROCESS-LOCAL / PASS`.
- Asset/Candidate/Timeline/Subtitle/TASK-041 mutation, external upload, paid Provider, model/training, install, Release, Deploy and Production effects: `NONE`.
- Intentional residuals: source/tests/docs, commit and required external Evidence checkpoint only.
- A4-R2b2 private-audio acceptance remains approved but dependency-pending until one exact suitable private WAV Asset exists in the canonical Product registry with matching TASK-041 source identity.
- A5 remains blocked on the exact canonical TASK-047 receipt ABI. A6 Product-native acceptance remains separate.
