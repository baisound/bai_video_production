# TASK-104 — Deterministic PowerShell Hash Resolution

Status: `COMPLETED / VALIDATED / COMMIT_READY / PUBLICATION_PENDING`

Governance: `DEV-3 HIGH ASSURANCE`

## Authority and responsibility

The Owner authorized this corrective Atomic Unit on 2026-10-10 to repair the transient child Windows PowerShell `Get-FileHash` module-resolution failure in the existing TASK-047/TASK-048 controller build script. The unit owns only the shared PowerShell hashing bootstrap. It does not reopen TASK-047, TASK-048 or TASK-096 and does not change Product, recording, packaging or release semantics.

Exact base and branch at Builder start:

- base / `origin/main`: `53e4f0ea8e219b773a2976ba40b956830ff2e1df`
- branch: `codex/task-104-powershell-hash-resolution`
- worktree: `C:\Users\user\.codex\worktrees\task104-powershell-hash-resolution\bai-video-production`

## Atomic Unit contract

The implementation must:

- resolve `Microsoft.PowerShell.Utility` from the running shell's immutable `$PSHOME` module tree rather than inherited `PSModulePath` search order;
- import the exact manifest path and verify both the import and qualified `Get-FileHash` command resolve inside that exact module root;
- invoke the verified command object for every SHA-256 calculation;
- fail closed when the shell home, module manifest, import identity, command identity or returned SHA-256 value is invalid;
- preserve Windows PowerShell 5.1 and PowerShell 7 compatibility;
- preserve one compiler invocation with no retry and preserve the existing output-containment guards unchanged.

No native build, installer, dependency acquisition, Release, Deploy, Resolve, Production, private-media or prior-output cleanup is authorized.

## Builder implementation

`native/task047_obs_voice_capture/scripts/build-controller.ps1` now imports the module by the exact `$PSHOME\Modules\Microsoft.PowerShell.Utility\Microsoft.PowerShell.Utility.psd1` manifest path. It rejects missing or reparse-point paths, verifies the imported module identity, and verifies the sole module-qualified `Get-FileHash` command has the expected module name. Its actual `Module.Path` must be an existing leaf inside the exact module root; every file/directory component from that leaf through the module root is identity-checked and rejected if it is a reparse point. The script retains that verified command object. `Get-TrustedSha256` validates the returned digest shape and is the only SHA-256 route used by schema, worker closure, controller receipt and receipt read-back hashing.

The compiler line remains exactly one `& $Compiler @arguments` invocation. Existing placement and containment logic is unchanged.

## Builder verification

Technical results:

- Windows PowerShell 5.1 parser: `PASS` (`5.1.26100.9549`).
- PowerShell 7 parser: `PASS` (`7.6.5`).
- focused TASK-104 plus direct controller/packaging/readiness regression: `60 PASS`.
- review/fix cycle 1 TASK-104 plus direct controller/packaging/readiness regression: `62 PASS`.
- initial narrower TASK-104/controller run: `15 PASS / 13 DESELECTED`.
- TASK-047 readiness-receipt module collection: `NOT_CONFIRMED` because the current Python 3.13 environment lacks the pre-existing `jsonschema` dependency; no dependency installation was attempted.

The focused tests cover clean child processes, controlled hostile `PSModulePath`, exact module-root verification, missing and invalid module failure, SHA-256 result identity, both installed PowerShell families, one compiler invocation/no retry, and output containment including direct drive-root-child refusal. No shell binary was skipped on this host.

Resolved test roots and intentional residuals:

- `C:\Users\user\AppData\Local\Temp\task104-builder-32241a2d66d344a4877910910b358c30` — focused passing run; retained.
- `C:\Users\user\AppData\Local\Temp\task104-builder-b42f7874ec5744abb64b68b8e2ee3a0e` — dependency-limited collection run; retained.
- `C:\Users\user\AppData\Local\Temp\task104-builder-ff2baa0834a24ba98fabfa675bb0467a` — 60-test passing run; retained.
- `C:\Users\user\AppData\Local\Temp\task104-builder-fix-6e4a46be36f148f9b386651ceda18675` — review/fix cycle 62-test passing run; retained.

An earlier test invocation without an explicit unique `--basetemp` reached a pre-existing ACL-denied pytest temp parent and produced no technical test result. It did not authorize or perform cleanup. No build, installer, Product runtime or external output root was created.

## Review/fix cycle 1

The independent Critic reported one Medium finding: the first implementation checked the qualified command's `Module.Path` lexically but did not independently require that path to be a leaf or reject reparse points in a deeper command-path directory. The bounded fix now requires the command file to be an existing leaf, verifies each observed path identity and walks the complete command-file-to-module-root chain while rejecting every reparse point. Controlled nested-directory symlink probes passed in both Windows PowerShell 5.1 and PowerShell 7; no symlink-privilege skip occurred.

The Critic's Low finding is parked: the historical TASK-042 test can obtain a false positive from the explanatory legacy-import comment. `tests/test_task042_windows_exe_build_contract.py` is outside TASK-104's frozen Allowed Files and was not changed. Its stale assertion does not execute or weaken the new resolver, and correcting that separate test contract requires separately authorized scope.

## Independent acceptance and completion

The corrected candidate was frozen at these SHA-256 values:

- controller script: `23280fdc26e12a5cded8144b8c48dc29eb706900357b5cc3f889be43a5bee225`;
- existing packaging test: `d5819d5737abed5a059a686b9feb4d76b45a8fd4c65df2594616db403a3b5e6a`;
- TASK-104 focused test: `672d76fc07f395c34d8402c1d52ab44bb40152ad05647b18891b0de1915a4577`.

The final independent Critic accepted the corrected candidate with `Critical 0 / High 0 / Medium 0 / Low 1`. The sole Low is the explicitly parked, out-of-scope TASK-042 stale comment-based assertion described above. The final independent Tester accepted with `Critical 0 / High 0 / Medium 0 / Low 0`; Windows PowerShell 5.1 and PowerShell 7 parsers passed, the corrected focused suite passed `30` tests with no skips, and the direct no-build TASK-047 controller/readiness regression passed `44` tests. Live nested command-path symlink rejection executed and passed in both shells.

This Atomic Unit is complete and commit-ready within its bounded claim. It proves deterministic shell-owned hash-command resolution and focused regression only. It does not prove a replacement Windows build: the consumed failed TASK-036 build remains preserved, and any replacement build, installer, Release, Deploy, Resolve or Production effect requires separate authority. Canonical tracked Evidence is `evidence/hash-resolution-corrective-20261010-r01.md`; the external Evidence checkpoint is under `C:\home\baisound\evidence\bai-video-production\TASK-104\powershell-hash-resolution\20261010-r01\`.

Publication remains pending. No push, pull request or merge authority was inferred from implementation authority.
