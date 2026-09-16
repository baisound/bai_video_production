# Building All Windows Release Artifacts

This is the developer runbook for the local, one-command Windows release build.
It builds artifacts only. It does not install or launch a Product, change OBS,
download a model/runtime, sign, tag, push, publish a GitHub Release, or deploy.

## Operator command

From a clean repository checkout on Windows:

```powershell
.\tools\windows\build-all-windows-release.ps1
```

The last two lines print the exact `SUMMARY.txt` and `artifacts` paths. A complete
run reports `result=PASS` and `exit_code=0` in `SUMMARY.txt`.

## One-time developer preparation

Use Python 3.12 with the repository build dependencies and the Python `build`
frontend. Dependency installation is deliberately separate from the build:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev,windows-build]" build
```

The following local inputs must already exist:

- Inno Setup 7.1.0 `ISCC.exe`, exact SHA-256
  `d06ebd38f38e3cee60a3c50cc45bd449d77e0bc6a5cabc607ea9886808e4de1a`;
- official PSF-signed `python-3.12.10-amd64.exe`, exact SHA-256
  `67b5635e80ea51072b87941312d00ec8927c4db9ba18938f7ad2d27b328b95fb`;
- Visual Studio Build Tools with the C# compiler expected by the existing Voice
  Capture Controller builder;
- the tracked TASK-047 runtime/source ZIPs, whose hashes are verified by preflight.

The default Python-installer location is
`.build-prerequisites\windows\python-3.12.10-amd64.exe`. This directory is ignored
by Git. Inno Setup is discovered from `BVP_ISCC_PATH`, standard Program Files, or
`ISCC.exe` on `PATH`. Use parameters when a machine has a different layout:

```powershell
.\tools\windows\build-all-windows-release.ps1 `
  -BuildPython 'C:\contained\build-env\Scripts\python.exe' `
  -IsccPath 'E:\contained\InnoSetup\7.1.0\ISCC.exe' `
  -PythonInstaller 'C:\contained\inputs\python-3.12.10-amd64.exe'
```

Paths above are examples only. Do not use a drive root or direct child of a drive
root for task output.

## Preflight without build effects

```powershell
.\tools\windows\build-all-windows-release.ps1 -PreflightOnly
```

Preflight validates the source/version, clean-worktree policy, output containment,
Python modules, pinned Inno compiler, pinned Python installer, and Voice Capture
inputs. It does not create a run directory. `-AllowDirtySource` is an explicit
diagnostic override; release candidates should remain clean.

## Output layout

Each run uses a new directory below `.artifacts\windows-release` by default:

```text
windows-release-<timestamp>-<id>/
  artifacts/
  logs/build.log
  SHA256SUMS.txt
  build-manifest.json
  SUMMARY.txt
  work/
```

`artifacts` contains the Python wheel/sdist, the main/Training/Trivia/Voice Model
Builder ZIPs, the Voice Capture runtime/source ZIPs, all six installers, and one
all-artifact bundle ZIP. The main ZIP retains the internal Key Helper, Meter
Worker, and Voice Capture Controller produced by the authoritative existing main
builder.

`build-manifest.json` records source identity, tool/input digests, stage results,
and each artifact's relative path, byte size, SHA-256, kind, and Product. The
transcript is local diagnostic evidence and may contain local paths; the manifest
and checksum list do not expose prerequisite paths.

## Safe output override and reruns

`-OutputRoot` must resolve inside the exact repository worktree. The script rejects
drive roots, direct children of drive roots, reparse-point ancestors, and an
existing run directory. `-RunId` is optional and must be new:

```powershell
.\tools\windows\build-all-windows-release.ps1 `
  -OutputRoot '.\.artifacts\windows-release' `
  -RunId 'manual-v0243-r01'
```

Never delete or reuse a failed run merely to make a retry pass. Diagnose its
`SUMMARY.txt` and `logs\build.log`, correct the prerequisite/source problem, and
run again with a new identity.

## Exit codes and diagnosis

| Code | Stage |
|---:|---|
| `0` | all artifacts, bundle, checksums, manifest, and summary passed |
| `2` | invalid argument or unsafe output path |
| `3` | prerequisite/source preflight |
| `10` | main EXE |
| `11` | DbD Training Studio EXE |
| `12` | DbD Trivia Editor EXE |
| `13` | Python wheel/sdist |
| `20` | main installer |
| `21` | DbD installers |
| `22` | Voice Model Builder EXE/installer |
| `23` | Voice Capture installer |
| `24` | Owner Voice Runtime installer |
| `30` | distribution staging/ZIP |
| `31` | checksum/manifest/read-back |
| `99` | unexpected orchestrator failure |

For `2` or `3`, correct the path, source state, or prerequisite named on stderr.
For a stage code, inspect the same stage in `logs\build.log`. Do not run any
installer as a troubleshooting step; build success is verified from output
existence, hashes, and manifest read-back only.

## Publication boundary

This script intentionally has no GitHub credentials or publication command. Tag
creation, push, GitHub Release publication, remote digest read-back, signing,
installation acceptance, and deployment remain separate Human-gated operations.
