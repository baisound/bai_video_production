# TASK-096 — One-command Windows Release Build Orchestrator

- Status: `A1_COMPLETE / IMPLEMENTATION_COMPLETE / CONTRACT_VERIFIED / A2_EFFECT_ZERO_PREFLIGHT_COMPLETE / USER_NATIVE_BUILD_BLOCKED_PREREQUISITES`
- Capability: `BVP-WINDOWS-RELEASE-BUILD-ORCHESTRATOR-001`
- Governance: `DEV-3 HIGH ASSURANCE`
- Owner authority: `2026-09-16` — Windows の全リリース成果物を、公開処理から分離した単一 PowerShell コマンドで構築できるようにする
- Base: `origin/main` / `v0.24.3` / `0daa3026e4436d28c9522c65127a04a90582efaa`
- Atomic Unit: `TASK-096/A1 — design, implementation, focused contract verification, and commit-ready evidence`

## Objective

Provide `tools/windows/build-all-windows-release.ps1` as the one-command local
Windows build entry point. It must reuse the repository's existing PyInstaller,
native controller, and Inno Setup builders; produce every TASK-095 release asset;
save detailed logs, SHA-256 values, a machine-readable manifest, and a concise
summary; and never tag, push, publish, install, launch a Product, download a model,
process Owner audio, or modify OBS.

## Design decision

### Artifact set and existing builders

| Artifact | Existing authoritative builder reused by A1 |
|---|---|
| Python wheel and source distribution | the same `python -m build` command as `.github/workflows/release.yml` |
| BAI Video Production one-dir EXE, internal Key Helper, Meter Worker, Voice Capture Controller | `build-windows-exe.bat` and its existing specs/native controller builder |
| BAI DbD Training Studio one-dir EXE | `build-dbd-training-studio-exe.bat` |
| BAI DbD Trivia Editor one-dir EXE | `build-dbd-trivia-editor-exe.bat` |
| Main installer | `tools/windows/build-task063-main-installer.ps1` |
| Training Studio and Trivia Editor installers | `tools/windows/build-task092-dbd-utility-installers.ps1` |
| Voice Model Builder EXE and installer | `tools/windows/build-task046-voice-model-builder-installer.ps1` |
| Voice Capture runtime/source ZIP and installer | tracked TASK-047 release assets plus `tools/windows/build-task047-obs-installer.ps1` |
| Owner Voice Runtime installer | `tools/windows/build-task093-owner-voice-runtime-installer.ps1` |

The orchestrator may stage or ZIP outputs, but it must not duplicate a Product's
PyInstaller or Inno Setup definition. The two DbD batch files may be amended only
to accept a fresh caller-owned output directory instead of overwriting `builds`.

### Safety and reruns

- The default parent is `<worktree>/.artifacts/windows-release`; every invocation
  creates a unique run directory below it.
- `-OutputRoot` selects a different parent only when it is an absolute contained
  descendant of this worktree. Drive roots, direct children of drive roots,
  reparse-point ancestors, existing run directories, and foreign output are
  rejected before build effects.
- A retry always receives a new run identity. A failed run remains available for
  diagnosis and is never repaired, deleted, or overwritten automatically.
- Pinned local prerequisites are read-only inputs. No dependency, model, or
  runtime acquisition occurs.

### Exit codes

| Code | Meaning |
|---:|---|
| `0` | all requested artifacts, ZIPs, checksums, manifest, and summary completed |
| `2` | invalid arguments or unsafe output path |
| `3` | preflight/prerequisite/source-state failure |
| `10`–`12` | main, Training Studio, or Trivia Editor EXE build failed |
| `13` | Python wheel/source-distribution build failed |
| `20`–`24` | main, DbD, Voice Model Builder, Voice Capture, or Owner Voice Runtime installer stage failed |
| `30` | distribution ZIP/staging failed |
| `31` | checksum, manifest, or final verification failed |
| `99` | unexpected orchestrator failure |

The first failing stage stops the run. The final summary records the stage and
the detailed transcript remains in the run directory.

### Log and manifest contract

Each successful run contains:

- `logs/build.log`: detailed transcript including child-builder output;
- `artifacts/`: standalone installers and distribution ZIPs;
- `SHA256SUMS.txt`: lowercase SHA-256 and relative POSIX-style artifact path;
- `build-manifest.json`: schema version, source commit/version/dirty state,
  operation identity, timestamps, tool/input digests, stage results, and every
  artifact's relative path, byte size, SHA-256, kind, and Product, plus the
  contained user-facing and internal EXE component inventory;
- `SUMMARY.txt`: short PASS/FAIL result, output location, manifest/checksum paths,
  and the failed stage when applicable.

No private absolute path is written into the public artifact manifest or checksum
file. The local transcript and summary may identify the run directory for the
operator.

## Verification plan

1. Static/contract tests for the single entry point, complete artifact matrix,
   existing-builder reuse, no publish/install/download verbs, exit-code mapping,
   and safe output invariants.
2. Windows effect-zero `-Help` and `-PreflightOnly` checks; the latter must not
   create a run directory.
3. Focused existing packaging/installer contract regression.
4. PowerShell parser check, Python compile/static checks where applicable, and
   `git diff --check`.
5. Full native artifact build remains an explicit user-executed command; this
   implementation task does not perform installation, model acquisition, Owner
   voice work, OBS mutation, tagging, pushing, or publication.

## Allowed files

- `tools/windows/build-all-windows-release.ps1`
- `build-dbd-training-studio-exe.bat`
- `build-dbd-trivia-editor-exe.bat`
- `tools/windows/build-task046-voice-model-builder-installer.ps1`
- `.gitignore`
- `tests/test_task096_windows_release_build_orchestrator.py`
- `docs/windows/WINDOWS-EXE-BUILD-INDEX.md`
- `docs/windows/BUILDING-ALL-WINDOWS-RELEASE.md`
- `README.md`
- `docs/ai-team/current-state.md`
- `docs/ai-team/tasks/TASK-096/**`

## Prohibited effects

- no direct push to `main`, force push, tag creation/movement, GitHub Release, or deploy;
- no paid/provider call, model/runtime download, Owner audio access or processing,
  training, Product launch, real installation, or OBS mutation;
- no output at a drive root/direct child, foreign-path overwrite, or cleanup of a
  previous run;
- no product version bump or `CHANGELOG.md` mutation.

## Acceptance

- one documented PowerShell command is the user-facing build entry point;
- all TASK-095 required Windows assets are produced or the command fails closed;
- existing builders/specs remain authoritative and are invoked rather than copied;
- preflight occurs before output creation, outputs are unique and contained, and
  existing artifacts are never overwritten;
- manifest, SHA-256 list, artifact inventory, summary, and detailed log are emitted;
- focused tests and required DEV-3 review responsibilities pass with zero unresolved
  Critical/High findings;
- durable Evidence is persisted and read back before the Atomic Unit is closed.

## A1 completion

- Focused/targeted contracts: `61 PASS / 1 intentionally deselected` (the
  prohibited real TASK-047 installer lifecycle test).
- PowerShell parser, effect-zero help, unsafe-output refusal, failed-preflight
  no-output behavior, focused compileall, and diff check: `PASS`.
- Critic findings: `0 Critical / 0 High / 0 Medium unresolved` after adding the
  explicit eight-EXE component inventory.
- Durable Evidence: `docs/ai-team/tasks/TASK-096/evidence/a1-contract-verification-20260916-r01.md`.
- Full native artifact production remains intentionally `NOT_EXECUTED`; the next
  action is the user's one-command run from a clean merged Windows checkout.

## A2 native preflight — 2026-09-22

- Exact clean merged source: `c3cd3a15fea82d7f6e9f761440fff7ade9ff982c`.
- `-PreflightOnly` stopped with exit code `3` before build effects because the
  default Inno Setup discovery did not find `ISCC.exe`.
- Output children remained `0 -> 0`; no run directory or artifact was created.
- The pinned Inno Setup 7.1.0 compiler was subsequently found at its documented
  read-only runtime coordinate and matched the required SHA-256.
- The official PSF-signed `python-3.12.10-amd64.exe` was not present in the
  documented worktree, TASK-093 Evidence/temp, or bounded known local coordinates.
- The installed CPython `3.12.10` candidate lacks the required `build` module.
- Full native artifact production therefore remains `NOT_EXECUTED`. No dependency
  or runtime was installed or downloaded. Resume only after a separately supplied
  pinned Python installer and a TASK-096-owned prepared build environment satisfy
  the existing preflight contract.
- Durable record: `evidence/a2-native-preflight-20260922-r01.md`.
