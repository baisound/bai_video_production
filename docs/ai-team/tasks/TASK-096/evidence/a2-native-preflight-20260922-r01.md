# TASK-096/A2 Native Preflight — 2026-09-22 r01

## Identity and result

- Active Project: `BAI VIDEO PRODUCTION`
- Task / Atomic Unit: `TASK-096 / A2_NATIVE_PREFLIGHT`
- Governance: `DEV-3 HIGH ASSURANCE`; this checkpoint is an effect-zero native prerequisite observation
- Branch: `codex/task-096-native-artifact-evidence`
- Exact source and current `origin/main`: `c3cd3a15fea82d7f6e9f761440fff7ade9ff982c`
- Source dirty before preflight: `false`
- Preflight result: `FAIL / exit code 3 / BLOCKED_PREREQUISITES`
- Full native artifact build: `NOT_EXECUTED`

## Executed preflight

The documented orchestrator was invoked with `-PreflightOnly` and the existing
installed CPython 3.12.10 coordinate. It stopped before build effects with:

```text
[ERROR] Inno Setup 7 ISCC.exe was not found. Configure BVP_ISCC_PATH or -IsccPath.
PREFLIGHT_EXIT_CODE=3
OUTPUT_CHILDREN_BEFORE=0
OUTPUT_CHILDREN_AFTER=0
```

The standard discovery path did not contain Inno Setup. The pinned compiler was
then found at the repository-documented read-only runtime coordinate and verified
without executing it.

## Read-only prerequisite audit

| Input | Observation |
| --- | --- |
| Inno Setup 7.1.0 `ISCC.exe` | present at documented runtime coordinate; SHA-256 `d06ebd38f38e3cee60a3c50cc45bd449d77e0bc6a5cabc607ea9886808e4de1a` |
| TASK-047 runtime ZIP | present; SHA-256 `03286e9efbf5dd5af38230dcf7fee4bf53eb3fcc7d7a6d014833b9996bc1f558` |
| TASK-047 source ZIP | present; SHA-256 `0ad4c83a957b37b455b38829f842f8318116c522cb542de0a9c5849567b29e72` |
| Voice Capture Controller C# compiler | present at the exact Visual Studio 18 Build Tools coordinate expected by the orchestrator |
| PSF `python-3.12.10-amd64.exe` | `NOT_FOUND` in the documented worktree location, bounded TASK-093 Evidence/temp roots, or known local coordinates |
| installed CPython | version `3.12.10`; required `build` module missing, so the dependency tuple cannot pass |

The TASK-049 build virtual environment is bound to another completed operation and
was not reused or repurposed for TASK-096.

## Effects and output roots

- Build/install/runtime output root: `NONE`
- `.artifacts/windows-release` child count: `0` before and `0` after preflight
- Intentional residual artifact from this A2 execution: `NONE`
- Drive-root/direct-child artifact: `0`
- Dependency/runtime download or installation: `0`
- Product installation/launch, Owner audio access, OBS mutation: `0`
- Signing, tag, push, GitHub Release, publication, deploy: `0`

## Resume conditions

Do not retry the full build with the same environment. Resume only when both are
supplied under the existing TASK-096 boundary:

1. the exact PSF-signed Python 3.12.10 installer with required SHA-256
   `67b5635e80ea51072b87941312d00ec8927c4db9ba18938f7ad2d27b328b95fb`;
2. a TASK-096-owned Python 3.12 build environment containing the declared
   repository Windows-build dependencies, including PyInstaller `6.22.2` and the
   `build`, `pywebview`, and `faster-whisper` packages.

Then rerun `-PreflightOnly` with explicit read-only prerequisite coordinates. A
full one-command build may start only after that preflight reports `PASS` and a
new unique run identity/output root is selected.
