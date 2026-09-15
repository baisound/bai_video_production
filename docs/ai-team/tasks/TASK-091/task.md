# TASK-091 — v0.24.0 Windows EXE / Installer Release Closure

- Status: `OWNER_AUTHORIZED_RELEASE_CANDIDATE`
- Atomic Unit: `V0-24-0-WINDOWS-RELEASE-R0`
- Governance: `DEV-4 FOUNDATION CRITICAL`
- Owner authority: 2026-09-16 に、Tag作成、全EXEのコンパイル、Release、
  およびインストールパッケージャーの同梱を明示承認。
- Base: `origin/main@7045e604781e2916bae317f998989d87fb36bf2c`
- Branch: `codex/release-20260916`

## Objective

`0.23.0` 以降の統合済み変更を次のminor release `0.24.0` として閉じる。
release PRの全required checks通過後、そのexact merged commitへannotated
`v0.24.0` Tagを付け、同一source identityからPython distribution、Windows
one-dir applications、全internal executable、統合per-user installerを生成し、
GitHub ReleaseへSHA-256付きで公開・再読込する。

## Release artifacts

1. `ai_video_production-0.24.0-py3-none-any.whl`
2. `ai_video_production-0.24.0.tar.gz`
3. `bai-video-production-0.24.0-windows-x64.zip`
4. `bai-dbd-trivia-editor-0.24.0-windows-x64.zip`
5. `bai-dbd-training-studio-0.24.0-windows-x64.zip`
6. `bai-video-production-0.24.0-windows-x64-setup.exe`
7. canonical TASK-047 OBS technical-preview assets retained by the existing
   release workflow
8. one complete `SHA256SUMS` covering the published release assets

The main one-dir payload must contain `BAI Video Production.exe`, the internal
`BAI Video Production Key Helper.exe`, the private meter worker, and the
voice-capture controller. The two DbD one-dir payloads must contain their named
user-facing EXEs. Every produced `.exe` is inventoried and hashed before upload.

## Allowed files and roots

Release-candidate source scope:

- `pyproject.toml`
- `PROJECT.md`
- `CITATION.cff`
- `CHANGELOG.md`
- `src/ai_video_production/__init__.py`
- `src/ai_video_production/connection_settings_web.py`
- `src/ai_video_production/subtitle_workspace_web.py`
- `docs/ai-team/current-state.md`
- `docs/ai-team/task-index.md`
- `docs/ai-team/tasks/TASK-091/**`

Build/output scope is the dedicated release worktree only. A unique operation
root beneath that worktree is resolved and checked before build. Durable
Evidence belongs beneath
`C:\home\baisound\evidence\bai-video-production\TASK-091\V0-24-0-WINDOWS-RELEASE-R0\<run-id>\`
and is read back before any stop or cleanup. No output may be written to a drive
root or direct child of a drive root.

## Gates and verification

- Product version constants, CITATION and exact CHANGELOG heading must agree.
- Release PR required checks and release-workflow full regression must pass.
- Windows build uses the pinned `windows-build` dependency set and records exact
  Python/PyInstaller/Inno Setup identities.
- Main, Trivia Editor, Training Studio and internal EXEs must exist, launch only
  where a bounded no-effect smoke exists, and be hashed.
- The unified installer must compile from the exact main payload and bind its
  payload-tree SHA-256. Building the installer is authorized; installing it is a
  separate native mutation and is not implied by this Unit.
- Annotated Tag, peeled commit, GitHub Release target and uploaded asset digests
  must all read back to the same exact release identity.
- Production activation, Provider/paid execution, private media/voice use,
  model/runtime download unrelated to the isolated build toolchain, Resolve or
  external application mutation remain prohibited.

## Completion

Completion requires exact PR/main/tag/workflow/release identities, green hosted
checks, successful Windows builds, installer compilation, complete local and
remote asset digest reconciliation, and a durable Evidence checkpoint. Until
then this Task remains a release candidate and no release claim is made.
