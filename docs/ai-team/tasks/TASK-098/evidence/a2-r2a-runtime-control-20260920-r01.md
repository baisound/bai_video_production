# TASK-098 A2-R2a Runtime Control Evidence

## Identity and scope

- Project / Task / Atomic Unit: `BAI VIDEO PRODUCTION / TASK-098 / A2-R2a`.
- Run identity: `20260920T093000+0900`.
- Worktree: `C:\home\baisound\projects\bai-video-production\.worktrees\task-098-universal-wav-review-integration`.
- Branch / pre-commit HEAD: `codex/task-098-universal-wav-review-integration` / `da6bd98867a35c36c46d9823e31cde71a07f7c73`.
- Base and current local `main`: `28ba61e5f01047a716c681a3584be22500fe53fc`.
- Governance: `DEV-3 HIGH ASSURANCE`.
- Authority: exact four-file R2a pure contract/schema/reducer allocation plus bounded TASK-098/current-state/task-index documentation.

## Implemented boundary

- Added six immutable, domain-separated runtime transcription control records,
  concrete `RuntimeTranscriptionLeaseFactV1`, immutable reducer facts and the
  pure `reduce_runtime_transcription_control` projection.
- Added an exact schema and byte-identical packaged mirror. Public output is the
  exact twelve-key body-free, phase-only projection.
- Added fail-closed operation status/attempt/ref, source, lease, slot, record
  family and predecessor-digest checks. Only an exact terminal closure commit
  can expose slot release. Only the two confirmed cancel closures claim a
  technical Provider stop; Human attestation remains separate.
- Added reducer priority, row 7/8, publication recovery, terminal closure,
  malformed/foreign coordinate and nested-type negative tests.

## Changed paths and hashes

All paths are inside the accepted R2a allocation.

- `src/ai_video_production/task098_runtime_transcription_control.py` — SHA-256 `741d4aa814d0e97194e08b879c15a46204bf8b7968f1df709297bd83a388dca1`.
- `schemas/task098-runtime-transcription-control.schema.json` — SHA-256 `0b132f67b39b82917f1e5df148ea6546acedad9f41b6d503a0180da7563d5c85`.
- `src/ai_video_production/schema_resources/task098-runtime-transcription-control.schema.json` — SHA-256 `0b132f67b39b82917f1e5df148ea6546acedad9f41b6d503a0180da7563d5c85`.
- `tests/test_task098_runtime_transcription_control.py` — SHA-256 `f1b1a85cd3041e44b228b4e50f6e0d45e93ed910987b9573d45d63999a9fe957`.
- This Evidence file and bounded canonical status documents are documentation-only completion updates.

## Verification

- Focused R2a: `40 PASS / 0 FAIL` in `1.68s`.
  - Runner: WSL Ubuntu `python3 -m pytest`.
  - Isolated root: `/tmp/bvp-task098-a2-r2a-20260920T090000-r08`.
- R2a plus direct R1a/R1b/R1c dependency regression: `454 PASS / 0 FAIL`
  in `56.95s`.
  - Isolated root: `/tmp/bvp-task098-a2-r2a-20260920T091000-r09`.
  - The temporary main-guard runner installed a process-local throwing stub for
    the unavailable and unused `Argon2id` import, invoked `pytest.main`, and was
    removed after the run. No dependency was installed and the selected tests
    did not instantiate the stub.
- Schema canonical/package mirror SHA-256: exact match.
- Post-format mirror/focused confirmation: `40 PASS / 0 FAIL` in `2.31s`,
  cache disabled, `/tmp/bvp-task098-a2-r2a-20260920T100000-r10`.
- Pytest cache warnings under the read-only worktree cache path did not affect
  the isolated test roots or results.
- An earlier runner without a main guard recursively re-entered under
  multiprocessing and is invalid harness Evidence. Its root
  `/tmp/bvp-task098-a2-r2a-20260920T071500-r01` is not used for acceptance.
- Independent Tester: static/schema/fix review `0/0/0/0`; independent pytest
  `NOT_CONFIRMED` because that agent could not see the worktree from WSL and the
  available Windows Python lacked pytest. No dependency installation was made.
- Independent Critic: initial `REJECT / 0 Critical / 1 High / 1 Medium / 0 Low`;
  final after bounded fixes `ACCEPT / 0/0/0/0`.
- Independent Judge focused execution: `40 PASS / 0 FAIL` in `1.60s`, direct
  WSL Ubuntu pytest with no stub and cache disabled. The prechecked unique root
  `/tmp/bvp-task098-a2-r2a-judge-20260920-692e5c93` is intentionally retained.
- Final Judge: `ACCEPT / COMMIT_READY / 0/0/0/0`. The Judge confirmed the
  independent execution plus Builder regression and static Tester combination
  satisfies the DEV-3 gate without claiming native or full-suite acceptance.
- External checkpoint: `C:\home\baisound\evidence\bai-video-production\TASK-098\a2-r2a-runtime-control\20260920T093000+0900\checkpoint.md`, SHA-256 `b9966804d2df0f74c6e8fb74960b3fd4fb6d0b62924114ab9d9d476f210fd34d`, read-back `PASS`.

## Safety and effects

- Store, Provider, TASK-036 engine/Shell, serialized launch config, native
  runtime, model execution/download, private media, Voice Dataset, training,
  Release, Deploy and Production Activation effects: `NOT_EXECUTED`.
- Build/QA/runtime output root: none. Test-only roots are the unique WSL `/tmp`
  paths listed above.
- Intentional residual artifacts: repository changes listed above, the external
  durable checkpoint and the independent Judge test root listed above. The
  temporary Builder regression runner was removed.
- R2b/R2c remain unallocated. TASK-097 second GPT-SoVITS learning remains local
  ChatGPT/Human-owned and was not touched.

## Next action

Commit the exact R2a files and bounded documentation, persist the commit receipt,
then perform a fresh R2b pre-mutation review. No R2b implementation may start
from this checkpoint alone.
