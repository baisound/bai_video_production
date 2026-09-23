# TASK-098 A3-R2 guarded model-settings evidence

- Date: `2026-09-22`
- Active Project: `BAI VIDEO PRODUCTION`
- Task / Atomic Unit: `TASK-098 / A3-R2`
- Run identity: `a3-r2-guarded-model-settings-20260922-r01`
- Governance: `DEV-3 HIGH ASSURANCE`
- Worktree: `C:\home\baisound\projects\bai-video-production\.worktrees\task-098-universal-wav-review-integration`
- Branch: `codex/task-098-a3-model-manager-settings`
- Pre-commit HEAD: `a2dca633e8f5398e56df435a456c3f37e51a8a2f`
- Base/current-main identity at unit start: `28ba61e5f01047a716c681a3584be22500fe53fc`
- Parent integration review: `PR #562`
- Result: `PASS / COMMIT_READY`

## Scope and implementation

A3-R2 adds a fake-only two-phase coordinator over the existing private TASK-036
launch configuration. It does not create a second settings store. Prepare is
read-only, validates the caller's exact config digest and Product Project
containment before invoking the injected model-folder picker, then stores the
selected path only in an expiring process-local pending record after A3-R1
validation.

Apply consumes the one-use confirmation, rechecks the config identity, existing
cache identity and exact A3-R1 inspection record, changes only `asr.model`,
preserves `allow_model_download=false`, validates the complete TASK-036 config,
and performs atomic replace with replacement-time CAS and stable read-back.
Shell prepare/apply output contains no path, model file metadata or exception
text. Service absence remains fail-closed and existing Product composition does
not auto-activate the new endpoints.

## Changed paths and ownership

All eleven paths are inside the accepted A3-R2 Allowed Files:

- `docs/ai-team/current-state.md`
- `docs/ai-team/task-index.md`
- `docs/ai-team/tasks/TASK-098/task.md`
- `docs/ai-team/tasks/TASK-098/a3-r2-guarded-model-settings-pre-mutation-review-20260922.md`
- `docs/ai-team/tasks/TASK-098/evidence/a3-r2-guarded-model-settings-20260922-r01.md`
- `src/ai_video_production/task098_faster_whisper_model_settings.py`
- `src/ai_video_production/task036_native_dialog.py`
- `src/ai_video_production/native_file_dialog.py`
- `src/ai_video_production/task036_shell_ui.py`
- `tests/test_task098_faster_whisper_model_settings.py`
- `tests/test_task036_shell_ui.py`

Allowed-files result: `PASS`. No foreign dirty path was overwritten. Schemas,
launch-config version/shape, Provider/runtime, dependencies, packages,
installer, Product version and private assets did not change.

## Artifact identities

- Design/review document: SHA-256
  `9de3d7f72beef0a869006560230b84c1d34e1d26402a8dfd5a03bec106674e85`,
  size `6812` bytes.
- Guarded model-settings coordinator: SHA-256
  `ee727ea52475d6fccba1eed3669dc776fa8446b8b38c4e21bae39f8af45fac36`,
  size `16494` bytes.
- TASK-036 dialog service: SHA-256
  `c4255f7769d7a8548479ff9297c82e9c750d0536688becd1a2dc96a8df570889`,
  size `7353` bytes.
- Fixed native dialog source: SHA-256
  `d8fc8ab51ca9e431740c2f9cb51a86ee5a2bb930e6f5282fad90a1b0eb9c3039`,
  size `15026` bytes.
- Shell bridge: SHA-256
  `1fe20835dc95bf00d49dd53098eb1fd03c9757d05d4e8cdc4e2ed9ddd720f905`,
  size `257717` bytes.
- A3-R2 tests: SHA-256
  `5df2df861c5a622a4ea12962c0f47b4e08ee45970a3c5c9c75fb98224e7533eb`,
  size `13882` bytes.
- Shell guard tests: SHA-256
  `73884f22c679380fb93e60c2328f5590dd5977277e3ca953aff7fdbb77d3c99a`,
  size `88218` bytes.

## Verification and review

- Direct ordinary WSL pytest collection: `NOT_CONFIRMED`; the environment's
  `cryptography` lacks Argon2id imported by an unrelated TASK-059 Shell module.
- No dependency was installed or changed. The established process-local unused
  Argon2id import stub was used only to load the Shell test graph.
- Focused A3 settings/picker/contracts: `131 PASS / 0 FAIL` in `4.50s`.
- TASK-036 Shell/trusted-launch regression: `113 PASS / 0 FAIL` in `24.36s`.
- Final combined eight-file WSL2 Ubuntu regression:
  `245 PASS / 0 FAIL` in `30.30s`.
- Windows fixed-interpreter route: `NOT_CONFIRMED` because it lacks
  `jsonschema`; no dependency was installed or changed.
- Python compile and Git diff check: `PASS`.
- Design Critic findings: `Critical 0 / High 4 / Medium 1 / Low 0`.
- Implementation Critic findings: `Critical 0 / High 2 / Medium 0 / Low 0`;
  corrected with read-only pre-lock Project containment and explicit semantic
  one-field diff validation.
- Final Critic findings: `Critical 0 / High 0 / Medium 0 / Low 0`.
- Tester: `PASS`.
- Judge: `ACCEPT / COMMIT_READY`.

## Output roots and prohibited effects

- Build/install/native/runtime output root: `NONE`.
- Test fixture/settings root: pytest-managed unique directories beneath
  `/tmp/pytest-of-baisound`; no Product/private model or audio path was read.
- Pytest cache: disabled.
- Repository Evidence root: this file under the TASK-098 tracked Evidence area.
- External durable Evidence destination:
  `C:\home\baisound\evidence\bai-video-production\TASK-098\a3-r2-guarded-model-settings\20260922T113210+09-00\checkpoint.md`.
- Intentional residual artifacts: the eleven tracked paths above plus the
  external durable checkpoint after commit.
- Prohibited and not executed: real Product settings mutation, real native
  picker, model construction/inference, Provider execution, download/network,
  private media/audio processing, recording, Dataset adoption, training,
  installation, Release, Deploy and Production Activation.

## Dependencies, gates and next action

TASK-006/023 FasterWhisper ownership, TASK-036 settings/Shell ownership,
TASK-041 review metadata, TASK-046 Dataset/Training/ModelCandidate, TASK-047
capture provenance and TASK-048 quality ownership remain canonical. The Owner's
Download-folder GitHub migration and local TASK-097 second training remain
outside this unit.

Remote branch push is parked: the external safety reviewer rejected repository
egress because destination ownership was not explicitly established. No bypass
or indirect push was attempted.

Next action: perform a fresh bounded A3-R3 design/authority review for cache
reuse/read-back and restart tests without model construction. A3-R2 does not
allocate that implementation.
