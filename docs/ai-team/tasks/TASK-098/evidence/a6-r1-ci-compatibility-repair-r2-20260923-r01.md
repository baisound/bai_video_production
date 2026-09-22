# TASK-098 A6-R1 CI Compatibility Repair R2 Evidence

## Identity

- Active Project: BAI VIDEO PRODUCTION
- Task: TASK-098
- Atomic Unit: A6-R1 CI compatibility repair R2
- Run ID: `20260923T004542+0900`
- Worktree: `C:\home\baisound\projects\bai-video-production\.worktrees\task-098-universal-wav-review-integration`
- Branch: `codex/task-098-a4-review-workspace`
- Pre-repair HEAD: `83e06683c67e9470fb715b5c894b10d93c920693`
- Existing PR: `#562`
- Failed hosted CI run: `35745131935`
- Base/current-main identity retained through merge commit
  `0b63eca497a3103e1ab296ad40d840ea0f0f992a` from
  `origin/main` `ae456f46d0124108740be92a0411b83ce5e1c75b`

## Hosted Evidence and Diagnosis

- PR head publication to `83e06683c67e9470fb715b5c894b10d93c920693`:
  `PASS`.
- Security dependency audit, secret scan and release-metadata checks: `PASS`.
- Test matrix Ubuntu 3.11/3.12/3.13 and Windows 3.11/3.12/3.13:
  `FAIL`.
- Linux exact shared failures: stale v2 transcription route marker, runtime
  Shell source counts, and deterministic inventory count/state expectations.
- Windows shared failures additionally showed unchanged files rejected because
  path `stat` and descriptor `fstat` expose different `st_ctime_ns` values.
- Windows headless runner also cannot satisfy a real audio-device acceptance
  test without explicit native authority/environment selection.

## Correction

- `task098_faster_whisper_model_directory_inspector.py` and
  `task098_faster_whisper_model_settings.py` use stable Windows physical
  identity/type/size/mtime fields plus `st_birthtime_ns` when available.
  POSIX retains its ctime mutation signal.
- V6.1.1 transcription and element inventory tests now bind the canonical
  composed TASK-098 Product Shell rather than pre-A6 values.
- Synthetic Windows audio-device acceptance requires explicit
  `BVP_TASK098_NATIVE_AUDIO=1`; absence is an intentional deselection, not a
  playback PASS.

## Local Verification

- Exact hosted failing-test group: `37 PASS / 1 SKIP`.
- Focused surrounding regression: `123 PASS / 1 SKIP`.
- Skip: explicit Windows-native audio-device acceptance not selected.
- Wider diagnostic: `657 PASS / 2 SKIP`; eight schema-semantic tests were not
  valid under the import-only `jsonschema` stub and two settings tests exceeded
  an existing 200-character field limit because the diagnostic basetemp was
  too long. These ten are harness limitations, not accepted Product results.
- Python compile: `PASS`.
- Git diff check: `PASS`.
- Real-dependency hosted CI after publication: `NOT_CONFIRMED`.
- External pre-commit checkpoint:
  `C:\home\baisound\evidence\bai-video-production\TASK-098\a6-r1-ci-compatibility-repair-r2\20260923T004542+0900\checkpoint.md`,
  SHA-256 `ebbd8a29f0de264a95b0fdc69f97e05a0ec54bf3d1078b48fb1b9c340a1422b8`,
  size `2859`, read-back `PASS`.

The local Python lacks `jsonschema` and `cryptography`. The process-local
stubs enabled imports only and are not Evidence of schema or crypto behavior.

## Scope and Safety

- Product/test changed paths are limited to two TASK-098 source files, three
  directly related tests, and bounded canonical TASK-098/current-state/index
  documentation.
- No private audio or native playback was executed in R2.
- No Asset automatic ingest, TASK-041 completion, model load/download,
  Dataset/training, package/install, Release, Deploy or Production effect
  occurred.
- No task artifact was placed at a drive root or direct child of a drive root.

## Preserved Residual Test Roots

Cleanup failed closed before deletion because pytest-created child directories
deny complete enumeration to the current process. Ownership/ACL takeover and
unsafe recursive deletion were not authorized or attempted. These roots are
not commit candidates and must not be reused:

- `.task098-ci-r2-test` — File ID
  `0x0000000000000000003400000002012b`
- `.t98` — File ID `0x0000000000000000000c000000322234`
- `.task098-ci-r2-stubs` — File ID
  `0x000000000000000000ac000000081d26`

## Next Action

Commit the exact reviewed R2 correction, publish it only to existing PR #562,
and require a successful hosted real-dependency matrix before recording the
CI repair complete. A5 remains blocked on the canonical TASK-047 receipt ABI.
