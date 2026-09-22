# TASK-098 A6-R2 Product Asset Selection Evidence

Date: `2026-09-23`
Result: `LOCAL PASS / HOSTED NOT YET EXECUTED`
Development depth: `DEV-3 HIGH ASSURANCE`

## Repository identity and scope

- Worktree:
  `C:\home\baisound\projects\bai-video-production\.worktrees\task-098-a6-r2-product-selection`.
- Branch: `codex/task-098-a6-r2-product-selection`.
- Bound base/current main:
  `454ddd1e2d0b87cb5ebb16a27dc75e6e1c745ff5`.
- Pre-commit HEAD:
  `454ddd1e2d0b87cb5ebb16a27dc75e6e1c745ff5`.
- Dirty state: exactly the 11 A6-R2 paths listed below; no unrelated tracked
  or untracked path exists in this dedicated worktree.
- Design:
  `../a6-r2-product-asset-selection-design-20260923.md`.
- Allowed-file review: `PASS`; no schema, store, ingest, TASK-041
  completion/decision, launch-config, packaging/installer/version, ASR/model,
  Release, Deploy or Production path changed.

Changed paths:

1. `docs/ai-team/current-state.md`;
2. `docs/ai-team/tasks/TASK-098/task.md`;
3. `docs/ai-team/tasks/TASK-098/a6-r2-product-asset-selection-design-20260923.md`;
4. this Evidence file;
5. `src/ai_video_production/task098_product_review_binding.py`;
6. `src/ai_video_production/task036_shell_ui.py`;
7. `src/ai_video_production/task036_trusted_launcher.py`;
8. `src/ai_video_production/task098_shell_html.py`;
9. `tests/test_task098_product_review_binding.py`;
10. `tests/test_task036_shell_ui.py`;
11. `tests/test_task036_trusted_launcher.py`.

## Repair result

A6-R1 had correctly connected the verified Runtime, confirmation protocol and
Shell display, but the normal Product entry chain supplied a private A4 binding
only in injected tests. A6-R2 now composes a process-local selector in the
normal trusted launch and reuses the existing TASK-041 Audio Workspace
Candidate projection, Product Asset registry and Logical Path resolver.

- Before Human selection the Product ViewModel remains byte-shape compatible:
  no Universal WAV Review projection is added and no file/media effect occurs.
- The Audio Workspace exposes `Universal WAV Reviewで確認` only when the
  normal selector is bound. The request carries only the current
  `candidate_id`.
- Selection revalidates current Project/Candidate lifecycle, production/audio
  snapshot digests, Asset/job/checksum/rights and a stable regular PCM WAV
  container. It reads bounded WAV header facts only; no PCM body decode,
  playback or waveform generation occurs.
- The selected binding is process-local, one Candidate only, one-hour
  observation-bounded and invalidated by Candidate/Asset/snapshot drift or
  launch close. It creates no canonical state.
- Existing A6-R1 prepare/confirm/apply remains the execution gate. Apply still
  independently verifies the entire Asset checksum, file identity, rights,
  WAV format and range before playback.
- A refresh race after currentness changes disables only the optional review
  surface; it cannot make the entire Product ViewModel unavailable.

## Verification

- Python compile for all changed Product modules: `PASS`.
- New selector unit and Shell-to-Runtime integration: `5 PASS`.
- Focused selector/application/Shell/launcher regression: `126 PASS`.
- Final TASK-098 plus direct TASK-041/TASK-036 regression:
  `625 PASS / 2 intentional native skips` in `264.83s`.
- Skips were the pre-existing explicit private-WAV and real Windows audio-device
  acceptance gates. No private WAV was supplied and no audio device was used.
- Git diff whitespace check: `PASS`.

The Windows validation environment was created beneath the OS temporary root
at:

- R01:
  `C:\Users\user\AppData\Local\Temp\bvp-task098-a6r2-tests-20260923-r01`;
  an incorrect stale Python 3.12 base identity made it unusable, and it was
  subsequently ownership-verified and removed.
- R02:
  `C:\Users\user\AppData\Local\Temp\bvp-task098-a6r2-tests-20260923-r02`;
  it used the existing Python 3.13 runtime and repository-declared real
  dependencies. Cleanup verified the exact Owner marker and non-reparse root,
  but stopped when pytest-owned `pytest-run-01` denied enumeration/removal.
  R02 remains an intentional residual; no ACL/ownership mutation, takeover,
  unsafe retry or reuse occurred.

The earlier WSL environment lacked the required Argon2id implementation for
Shell-wide collection; the new selector-only boundary nevertheless passed
`4 PASS` there. No dependency was changed in the Product or system runtimes.

## Review findings

The final high-reasoning diff review checked canonical ownership, default
effect-zero behavior, stale selection/replay, cross-job and rights controls,
path/body disclosure, lifecycle cleanup and exception/race handling.

- Truthful selection status now distinguishes `wav_header_read=true` from
  `audio_body_read=false`.
- A Candidate-currentness race now removes only the optional review projection.
- Malformed binding clocks/contracts and Candidate-provider failures now cross
  the Shell boundary as closed Product errors.
- Final unresolved findings: `Critical 0 / High 0 / Medium 0 / Low 0`.

## Retained boundaries

No automatic Asset selection or ingest, arbitrary path input, receipt,
TASK-041 completion or Human decision, review persistence, Dataset adoption,
training, model/voice-server activation, private native playback, package or
installer change, Release, Deploy or Production activation occurred.

A5 remains blocked on the exact canonical TASK-047 receipt ABI/parser and a
fresh DEV-4 review. Hosted real-dependency verification is the next A6-R2
closure step.

## Durable external checkpoint

- Path:
  `C:\home\baisound\evidence\bai-video-production\TASK-098\a6-r2-product-asset-selection\20260923T034742+0900\checkpoint.md`.
- SHA-256:
  `1be7a557d8fcf1a7bc279c05bab1eac1907fd3b8fc8f656f678d5e6eead075e4`.
- Size: `5,509` bytes.
- Read-back identity/result: `PASS`.
