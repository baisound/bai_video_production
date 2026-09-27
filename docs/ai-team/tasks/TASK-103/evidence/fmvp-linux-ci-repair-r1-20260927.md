# TASK-103 Hosted Linux CI Repair R1

- Project / Task: `BAI VIDEO PRODUCTION / TASK-103`
- Atomic Unit: `FMVP-HOSTED-CI-R1`
- Branch: `codex/task-103-linux-ci-repair`
- Base `main` / `origin/main`: `51870bd5720cbedd80c15fe657df495384b4c9ed`
- Worktree: `C:\home\baisound\projects\bai-video-production\.task047-status-sync-20260924`
- Result: `PASS`

## Failure and correction

PR #586 CI run `36320597403`, Ubuntu 3.11 job `108623552918`, completed `8726 PASS / 126 SKIP / 2 FAIL`. Both failures were in the new GPT-SoVITS renderer tests: Linux `tmp_path` was passed to the WSL-path translator, which previously accepted only a Windows drive path.

The correction changes only the existing TASK-014 GPT-SoVITS reference-path boundary and its focused test. `server_path_mode=wsl` still maps a Windows local drive path to `/mnt/<drive>/...`; when the caller already runs on a POSIX host, a resolved POSIX absolute path is returned unchanged. Relative/nonexistent inputs remain rejected by strict resolution, and unsupported path forms remain fail-closed.

## Verification and scope

- Focused/direct TASK-014, TASK-073 and TASK-100 regression on Linux: `226 PASS`.
- `git diff --check`: `PASS`.
- Changed paths: `src/ai_video_production/task014_srt_owner_voice_wav.py`, `tests/test_task014_srt_owner_voice_wav.py`, this Evidence file and TASK-103 completion record.
- Allowed Files: `PASS`; these paths are within the existing FMVP-I1 implementation/test/Evidence boundary.
- Test root: dedicated worktree-contained `.test-runs/task103-linux-ci-repair-20260927-r1`; removed after PASS.
- No server/model/private-audio/native/Project/Asset/Release/Deploy/Production effect occurred.

The accepted Master WAV and its digest are unchanged. This corrective only restores hosted cross-platform verification of the completed functional MVP.
