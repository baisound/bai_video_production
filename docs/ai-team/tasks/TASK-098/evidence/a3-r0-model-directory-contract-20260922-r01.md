# TASK-098 A3-R0 model-directory contract evidence

- Date: `2026-09-22`
- Active Project: `BAI VIDEO PRODUCTION`
- Task / Atomic Unit: `TASK-098 / A3-R0`
- Run identity: `a3-r0-model-directory-contract-20260922-r01`
- Governance: `DEV-3 HIGH ASSURANCE`
- Worktree: `C:\home\baisound\projects\bai-video-production\.worktrees\task-098-universal-wav-review-integration`
- Branch: `codex/task-098-a3-model-manager-settings`
- Pre-commit HEAD: `4ce43e43fb9bb4b80f86302142ba99422c70ea9e`
- Base/current-main identity: `28ba61e5f01047a716c681a3584be22500fe53fc`
- Parent integration review: `PR #562`
- Result: `PASS / COMMIT_READY`

## Scope and implementation

A3-R0 adds only the pure, body-free validation boundary needed before any local
FasterWhisper model-directory read is authorized. It defines immutable file
observations, a closed READY/BLOCKED inspection record, exact canonical/package
schema mirrors, deterministic manifest/record identities and a minimized public
projection. It performs no filesystem read, settings mutation, model load,
inference, network call, download or private-audio processing.

READY requires `config.json`, `model.bin`, `tokenizer.json` and exactly one of
`vocabulary.txt` / `vocabulary.json`. `preprocessor_config.json` is optional.
Only the closed allowlist is accepted. File-specific size bounds, SHA-256
digests, state/reason combinations and effect flags fail closed.

## Changed paths and ownership

All paths are inside the TASK-098 Product integration boundary and the active
worktree:

- `docs/ai-team/current-state.md`
- `docs/ai-team/task-index.md`
- `docs/ai-team/tasks/TASK-098/task.md`
- `docs/ai-team/tasks/TASK-098/a3-r0-model-directory-contract-pre-mutation-review-20260922.md`
- `docs/ai-team/tasks/TASK-098/evidence/a3-r0-model-directory-contract-20260922-r01.md`
- `schemas/task098-faster-whisper-model-directory.schema.json`
- `src/ai_video_production/schema_resources/task098-faster-whisper-model-directory.schema.json`
- `src/ai_video_production/task098_faster_whisper_model_directory.py`
- `tests/test_task098_faster_whisper_model_directory.py`

Allowed-files result: `PASS`. No foreign dirty path was overwritten.

## Artifact identities

- Design/review document: SHA-256
  `8cc3646406fb7cbfbe73a49a21424eb70272e44294ad7a3405335cd1e7e099c9`,
  size `8464` bytes.
- Canonical schema mirror: SHA-256
  `45064bed5451675213737c00d3366e723e0149bffabfaf53d40f7db171aedd40`,
  size `8994` bytes.
- Package schema mirror: same SHA-256 and size as the canonical schema.
- Python contract: SHA-256
  `cbbb614e2996425a96ddb3645f51f5c562034ad14e055191c7d712898b819b08`,
  size `15669` bytes.
- Focused tests: SHA-256
  `84470b715726dec2a977784059a072fc189fbb9cfda241fa1202d0eee93362f9`,
  size `10724` bytes.

## Verification and review

- Focused A3-R0 plus direct A2 runtime-contract regression in WSL2 Ubuntu:
  `87 PASS / 0 FAIL` in `3.58s`.
- Windows fixed-interpreter route: `NOT_CONFIRMED` because that interpreter
  lacks `jsonschema`; no dependency was installed or changed.
- Python compile: `PASS`.
- Canonical/package JSON parse and byte-for-byte schema mirror: `PASS`.
- Git diff check: `PASS`.
- Critic cycle initial findings: `Critical 0 / High 3 / Medium 1 / Low 0`.
- Corrections: file-specific schema size bounds, complete READY file
  composition, public READY/BLOCKED cross-products and negative schema tests.
- Final Critic findings: `Critical 0 / High 0 / Medium 0 / Low 0`.
- Tester: `PASS`.
- Judge: `ACCEPT / COMMIT_READY`.

## Output roots and prohibited effects

- Build/install/native/runtime output root: `NONE`.
- Pytest cache: disabled; no cache artifact intentionally retained.
- Repository Evidence root: this file under the TASK-098 tracked Evidence area.
- External durable Evidence destination:
  `C:\home\baisound\evidence\bai-video-production\TASK-098\a3-r0-model-directory-contract\20260922T104227+09-00\checkpoint.md`.
- Intentional residual artifacts: the nine tracked paths above plus the external
  durable checkpoint after commit.
- Prohibited and not executed: filesystem inspection, launch-config/settings
  mutation, native picker, real Provider/model execution, download/network,
  private media/audio processing, recording, Dataset adoption, training,
  installation, Release, Deploy and Production Activation.

## Dependencies, gates and next action

TASK-006/023 FasterWhisper ownership, TASK-036 settings/Shell ownership,
TASK-041 review metadata, TASK-046 Dataset/Training/ModelCandidate, TASK-047
capture provenance and TASK-048 quality ownership remain canonical. The Owner's
Download-folder GitHub migration and local TASK-097 second training remain
outside this unit.

Next action: perform a fresh bounded A3-R1 design/authority review for a
contained read-only filesystem inspector. A3-R0 does not allocate that
implementation.
