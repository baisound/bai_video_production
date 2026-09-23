# TASK-098 A3-R1 model-directory inspector evidence

- Date: `2026-09-22`
- Active Project: `BAI VIDEO PRODUCTION`
- Task / Atomic Unit: `TASK-098 / A3-R1`
- Run identity: `a3-r1-model-directory-inspector-20260922-r01`
- Governance: `DEV-3 HIGH ASSURANCE`
- Worktree: `C:\home\baisound\projects\bai-video-production\.worktrees\task-098-universal-wav-review-integration`
- Branch: `codex/task-098-a3-model-manager-settings`
- Pre-commit HEAD: `fdab459d079791edf88a3e1c8be9d09b9952e132`
- Base/current-main identity at unit start: `28ba61e5f01047a716c681a3584be22500fe53fc`
- Parent integration review: `PR #562`
- Result: `PASS / COMMIT_READY`

## Scope and implementation

A3-R1 adds only a contained read-only inspector over the A3-R0 contract. It
accepts one explicit absolute local locator, checks symlink/reparse ancestry,
strictly resolves the directory, caps its top-level enumeration at 64 entries
and reads only the six allowlisted model filenames.

Each admitted file must be a single-link regular file and retain the same
physical identity before open, through the no-follow descriptor read and after
close. Content is SHA-256 hashed in bounded chunks. Present allowlisted JSON is
parsed as UTF-8 JSON from the stable read. BLOCKED results contain no partial
file observations, paths or exception text. The implementation contains no
settings, model, Provider, network, download or audio operation.

## Changed paths and ownership

All eight paths are inside the accepted A3-R1 Allowed Files:

- `docs/ai-team/current-state.md`
- `docs/ai-team/task-index.md`
- `docs/ai-team/tasks/TASK-098/task.md`
- `docs/ai-team/tasks/TASK-098/a3-r1-model-directory-inspector-pre-mutation-review-20260922.md`
- `docs/ai-team/tasks/TASK-098/evidence/a3-r1-model-directory-inspector-20260922-r01.md`
- `src/ai_video_production/task098_faster_whisper_model_directory.py`
- `src/ai_video_production/task098_faster_whisper_model_directory_inspector.py`
- `tests/test_task098_faster_whisper_model_directory_inspector.py`

Allowed-files result: `PASS`. No foreign dirty path was overwritten. Schemas,
TASK-036 settings/Shell, Provider/runtime, dependencies, packages, installer,
version and private assets did not change.

## Artifact identities

- Design/review document: SHA-256
  `3e895d1ee1018432649691276183b57b9a6c6062cac6594785e4d7e499d9e363`,
  size `6543` bytes.
- A3-R0 contract with exported immutable constants: SHA-256
  `12d3103a44a25a0d13abe6ce8c589249a63c398c3301bcb41ade8c3765d99d7a`,
  size `16051` bytes.
- Read-only inspector: SHA-256
  `7d1db17bb98c008edf31bf2979b7a8802e985a644efa9e79cd0f2aafcc3034a5`,
  size `8161` bytes.
- Inspector tests: SHA-256
  `803e405f8d50057c37c21c3bd7a87a15e23682a63d38e83d08f03f973de39fa8`,
  size `10094` bytes.

## Verification and review

- Initial A3-R1/A3-R0/direct A2 contract cycle:
  `102 PASS / 1 FAIL`; one reason-classification ordering defect.
- Correction: symbolic/reparse alias first, then regular-file type, then
  multi-link alias. No contract/schema change was required.
- Final WSL2 Ubuntu A3-R1/A3-R0/direct A2 contract regression:
  `106 PASS / 0 FAIL` in `3.80s`.
- Windows fixed-interpreter route: `NOT_CONFIRMED` because that interpreter
  lacks `jsonschema`; no dependency was installed or changed.
- Python compile and Git diff check: `PASS`.
- Critic initial findings: `Critical 0 / High 3 / Medium 1 / Low 0`.
- Final Critic findings: `Critical 0 / High 0 / Medium 0 / Low 0`.
- Tester: `PASS`.
- Judge: `ACCEPT / COMMIT_READY`.

## Output roots and prohibited effects

- Build/install/native/runtime output root: `NONE`.
- Test fixture root: pytest-managed unique directories beneath
  `/tmp/pytest-of-baisound`; no Product/private asset path was read.
- Pytest cache: disabled.
- Repository Evidence root: this file under the TASK-098 tracked Evidence area.
- External durable Evidence destination:
  `C:\home\baisound\evidence\bai-video-production\TASK-098\a3-r1-model-directory-inspector\20260922T110511+09-00\checkpoint.md`.
- Intentional residual artifacts: the eight tracked paths above plus the
  external durable checkpoint after commit.
- Prohibited and not executed: settings mutation, native picker, model
  construction/inference, Provider execution, download/network, private
  media/audio processing, recording, Dataset adoption, training, installation,
  Release, Deploy and Production Activation.

## Dependencies, gates and next action

TASK-006/023 FasterWhisper ownership, TASK-036 settings/Shell ownership,
TASK-041 review metadata, TASK-046 Dataset/Training/ModelCandidate, TASK-047
capture provenance and TASK-048 quality ownership remain canonical. The Owner's
Download-folder GitHub migration and local TASK-097 second training remain
outside this unit.

Next action: perform a fresh bounded A3-R2 design/authority review for an
expected-digest guarded update of the existing private TASK-036 ASR model/cache
fields. A3-R1 does not allocate that implementation.
