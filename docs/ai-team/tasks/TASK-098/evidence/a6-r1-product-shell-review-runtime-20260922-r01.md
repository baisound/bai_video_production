# TASK-098 A6-R1 Product/Shell Review Runtime Evidence

Date: `2026-09-22`
Result: `PASS`
Development depth: `DEV-3 HIGH ASSURANCE`

## Pre-commit repository identity

- Worktree:
  `C:\home\baisound\projects\bai-video-production\.worktrees\task-098-universal-wav-review-integration`.
- Branch: `codex/task-098-a4-review-workspace`.
- Pre-commit HEAD: `86aca1297afe51320940ca7dbd8869d1fb641265`.
- Bound base/current local main: `28ba61e5f01047a716c681a3584be22500fe53fc`.
- Dirty state: exactly 14 A6-R1 changed paths; no unrelated dirty path. The
  allowed inventory below additionally notes one unchanged exercised test.

Allowed-file check `PASS`:

- `docs/ai-team/current-state.md`
- `docs/ai-team/tasks/TASK-098/task.md`
- `docs/ai-team/tasks/TASK-098/a6-r1-product-shell-review-runtime-design-20260922.md`
- this Evidence file
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/task036_trusted_launcher.py`
- `src/ai_video_production/task098_review_media_runtime_windows.py`
- `src/ai_video_production/task098_review_workspace_shell_projection.py`
- `src/ai_video_production/task098_review_shell_application.py`
- `tests/test_task036_shell_ui.py`
- `tests/test_task036_trusted_launcher.py`
- `tests/test_task098_review_media_runtime_windows.py` (native runtime is exercised; file unchanged)
- `tests/test_task098_review_workspace_shell_projection.py`
- `tests/test_task098_review_shell_application.py`
- `tests/test_task098_a6_windows_native_acceptance.py`

The actual changed set is the list above except the unchanged runtime test file.
All paths satisfy the A6-R1 allocation; schemas, stores, ingest, TASK-041,
ASR/model configuration, packaging, installer and version files are unchanged.

## Scope and authority

The Owner authorized the limited connection of the verified WAV review runtime
to the normal BVP Product/Shell, with canonical Asset private playback and
waveform display only after a Human operation, plus bounded native validation.
Automatic Asset ingest, TASK-041 completion, training, Release, Deploy and
Production use were excluded and did not occur.

## Implementation result

- Normal trusted-launch composition accepts only an explicit private A4 binding
  provider and constructs the concrete registry-bound Windows runtime from its
  own Product store/resolver.
- Unbound launch, ViewModel refresh and Edit-page navigation start no media
  effect.
- Shell uses exact prepare/cancel/apply routes and `window.confirm`.
- Confirmation is process-local, one-use, 300-second, capacity-bounded and
  stale-request-safe.
- Successful display data is capped to 2,048 normalized integer peaks inside
  the concrete runtime. No high-resolution envelope, PCM, path, Asset ID,
  digest, text or receipt crosses the Shell bridge.
- Launcher close invalidates pending confirmation state before closing the
  Product store.

## Windows-native acceptance

- Source identity: the previously accepted TASK-097 V2 final reference,
  SHA-256 `c356ff98f7e7ec6b574da03af8cf4b812a200fef35f75bde30f0128d2ff84899`.
- Source metadata: 48,000 Hz, mono, 24-bit PCM, 290,159 samples.
- Requested range: `[0, 48000)`.
- Runtime result: `SUCCEEDED`.
- Playback observed: `true`.
- Waveform observed: `true`.
- Local Shell display envelope: `2,048` normalized points.
- Canonical receipt created: `false`.
- Review/TASK-041 completion claimed: `false`.
- Review state persisted: `false`.
- Human decision authorized: `false`.
- Media mutation started: `false`.

The source remained read-only. Each native run used a unique pytest-owned
directory beneath the Windows system temporary root. The exact final run root
was `C:\Users\user\AppData\Local\Temp\pytest-of-user\pytest-1917`; its private
WAV copy and test database were removed after physical containment/creation-time
verification. Final intentional residual artifacts: none.

## Verification

- New Launcher/Shell/application focused gate: `6 PASS`.
- Post-Critic Shell/runtime focused regression: `86 PASS / 1 intentional
  Windows-native deselection`.
- Windows-native private acceptance: `1 PASS`.
- Earlier full Trusted Launcher regression before the bounded lifecycle
  correction: `56 PASS`; the final broader gate revalidates the corrected
  launcher and is recorded below.
- Final TASK-098/TASK-036 integration regression:
  `192 PASS / 2 intentional Windows-native deselections` in `57.94s`.
- Python compile: `PASS`.
- Git diff check: `PASS`.
- Final Critic findings: `Critical 0 / High 0 / Medium 0 / Low 0`.

## Boundaries retained

No automatic Asset ingest/selection, arbitrary path input, TASK-041 decision or
completion write, ASR/model activation, recording, Dataset adoption, training,
package/installer change, Release, Deploy or Production activation occurred.
A5 remains blocked on the canonical TASK-047 receipt ABI and fresh DEV-4 review.

## Durable external checkpoint

- Path:
  `C:\home\baisound\evidence\bai-video-production\TASK-098\a6-r1-product-shell-review-runtime\20260922T193332+0900\checkpoint.md`.
- SHA-256:
  `c8d430e02309f6aa790c829621d80a831777f78e0524f37d5bd88806477b31c3`.
- Size: `2,431` bytes.
- Read-back identity/result: `PASS`.
