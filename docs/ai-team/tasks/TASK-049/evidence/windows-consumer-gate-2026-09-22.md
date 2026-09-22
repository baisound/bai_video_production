# TASK-049 Windows Consumer Gate Evidence — 2026-09-22

## Result

- Active Project: `BAI VIDEO PRODUCTION`
- Task / Atomic Unit: `TASK-049 / WINDOWS_CONSUMER_GATE`
- DEV profile: `DEV-3 HIGH ASSURANCE`
- Run ID: `20260922T-task049-consumer-gate-4a5fba7a`
- Result: `PASS`
- Native-run branch: `codex/task-049-consumer-gate-native-evidence`
- Native-run source HEAD: `4a5fba7a835b2924548adfe73c863c0b3197d1fb`
- Native-run observed `origin/main`: `41aa93e65420db830c2fd54be1a2369042f659aa`
- Native-run dirty state: `false`

The dedicated branch was then rebased onto that current `origin/main`. Its TASK-049 implementation/test trees were byte-equivalent before and after rebase (`TASK049_TREE_EQUIVALENT=PASS`); the intervening main delta added only TASK-021-owned files. No TASK-021 dashboard or TASK-036 edit-UI file was modified by this unit.

## Packaged Windows observations

| Package | Observation | Result | SHA-256 |
| --- | --- | --- | --- |
| `BAI Video Production.exe` | Game Intelligence created `NEEDS_REVIEW`, accepted explicit Human Confirm, restarted, and read back `CONFIRMED` | `PASS` | `64a9f1bb9fa3c5af3ca5f2c5d7a83c16d5f38bbd2c006c8d04ad11e6ef4be8b4` |
| `BAI DbD Trivia Editor.exe` | built, launched twice, then canonical store read back the synthetic item as `CANDIDATE` | `PASS` | `abb63ba3e200b0ee77a53f57160564da9ded29dd0a5fcc943bb633bcaa51451c` |
| `BAI DbD Training Studio.exe` | built, launched twice, and read back the seeded workspace template | `PASS` | `91d753be8f44dc1b5c54c39976279ed3811e189e03057a0f4b8d50f95ac4f03c` |

The main BVP artifact was built from exact source `9734750a1524904feba525a34190ed07c8976a2c`. Its standalone R9B2 receipt was copied into the final Evidence set only after exact receipt and EXE hashes matched. The final combined receipt records that reuse explicitly.

## Fixture and claim boundary

- Rights basis: `SYNTHETIC_CREATED_FOR_LOCAL_TEST`
- Real media used: `false`
- Private media used: `false`
- New Human Gold labels created: `false`
- Trivia status: `CANDIDATE`
- ROI/Human Gold preparation: `PASS`
- Real rights-confirmed media ROI calibration: `NOT_CONFIRMED`
- Human Gold KPI: `NOT_CONFIRMED`
- Reason: real rights-confirmed DbD media and new Human labels were not supplied.

No audio use, learning/training, Provider execution, model/runtime acquisition, Production Timeline mutation, Resolve write, release, deploy, or Production Activation occurred.

## Verification

- Packaged Windows Consumer Gate: `PASS`
- All 29 `tests/test_task049*.py` files: `188 PASS` in `18.91s`
- New fixture `compileall`: `PASS`
- Both TASK-049 PowerShell harnesses parse: `PASS`
- Post-rebase TASK-049 tree-equivalence check: `PASS`
- Final receipt read-back: `PASS`
- Final receipt SHA-256: `5c5cce48dcba29fc082b4ab8400796c3bd8e168545ac2b52c28cd8c4ef930d6f`
- Main R9B2 receipt SHA-256: `c98e8ca740c647c143c13b70d577e50c1ad5b48750fa194a4a29dc25e19ea35a`
- Canonical fixture read-back receipt SHA-256: `649485c88256741110966b0d1aab6314b6509a3b7289750116ebfded6c8f8cee`

## Paths and residual artifacts

- Durable Evidence: `C:\home\baisound\evidence\bai-video-production\TASK-049\windows-consumer-gate\20260922T-task049-consumer-gate-4a5fba7a`
- Main package build: `<TASK-049 worktree>\builds\t49\de5c6b35c8c2`
- Utility build/runtime: `%TEMP%\bai-video-production\TASK-049\windows-consumer-gate\20260922T-task049-consumer-gate-4a5fba7a`
- Exact build Python environment: `%TEMP%\bai-video-production\TASK-049\build-python\20260922-consumer-gate-001`
- Main R9B2 process runtime: `%TEMP%\bai-task049-r9b2-38cf6a954078438fb2bdac083d66e752`

These are intentional residual artifacts retained for review. No cleanup or reuse is authorized by this checkpoint. No artifact was created at a drive root or as a direct child of a drive root.

## Changed-path and next-action boundary

This unit changes only TASK-049 Windows harness/fixture tests and scripts plus this TASK-049/current-state Evidence update. It reuses the existing Game Intelligence and canonical Timeline/Store boundaries and creates no standalone Game Intelligence application.

Next action requires a separate Human/data gate: supply rights-confirmed real DbD media and newly authorized Human labels, then run calibrated ROI, labeled/video-derived slice-reference, Human Gold KPI, and threshold-tuning evidence. Until then, production accuracy remains unclaimed.
