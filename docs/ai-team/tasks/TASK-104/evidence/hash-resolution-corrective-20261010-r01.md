# TASK-104 deterministic PowerShell hash resolution Evidence

## Identity and scope

- Project: `BAI VIDEO PRODUCTION`
- Task / Atomic Unit: `TASK-104 / deterministic PowerShell hash resolution corrective`
- Run identity: `task104-powershell-hash-resolution-20261010-r01`
- Worktree: `C:\Users\user\.codex\worktrees\task104-powershell-hash-resolution\bai-video-production`
- Branch: `codex/task-104-powershell-hash-resolution`
- Base and pre-commit HEAD: `53e4f0ea8e219b773a2976ba40b956830ff2e1df`
- Base/current remote main at allocation: `53e4f0ea8e219b773a2976ba40b956830ff2e1df`
- Governance: `DEV-3 HIGH ASSURANCE`
- Technical result: `PASS`
- Unit state: `COMPLETED / COMMIT_READY / PUBLICATION_PENDING`

The first unused Task-ID and responsibility audit found no TASK-104 on exact main, zero nonclosed entries in `ACTIVE-WORK-LOCKS.json`, and zero open pull requests. The frozen Allowed Files were the shared controller script, its existing packaging test, one new TASK-104 focused test, TASK-104 documentation/Evidence, and completion-only current-state/task-index synchronization. `ACTIVE-WORK-LOCKS.json`, `CHANGELOG.md`, existing TASK-036/TASK-047/TASK-096 records and all Product/runtime files were excluded.

## Changed paths and ownership

All changed paths are inside the frozen Allowed Files:

- `native/task047_obs_voice_capture/scripts/build-controller.ps1`
- `tests/test_task036_packaging.py`
- `tests/test_task104_powershell_hash_resolution.py`
- `docs/ai-team/tasks/TASK-104/task.md`
- `docs/ai-team/tasks/TASK-104/evidence/hash-resolution-corrective-20261010-r01.md`
- `docs/ai-team/current-state.md`
- `docs/ai-team/task-index.md`

The final corrected implementation/test candidate SHA-256 identities reviewed independently were:

- controller: `23280fdc26e12a5cded8144b8c48dc29eb706900357b5cc3f889be43a5bee225`
- existing packaging test: `d5819d5737abed5a059a686b9feb4d76b45a8fd4c65df2594616db403a3b5e6a`
- TASK-104 focused test: `672d76fc07f395c34d8402c1d52ab44bb40152ad05647b18891b0de1915a4577`

## Implementation result

The controller imports the exact `$PSHOME\Modules\Microsoft.PowerShell.Utility\Microsoft.PowerShell.Utility.psd1` manifest instead of resolving through inherited `PSModulePath`. It verifies the import identity, the sole module-qualified `Get-FileHash` command, the command file as an existing leaf, and every observed file/directory identity from that leaf through the exact module root. Reparse points, root escape, missing/invalid modules and non-64-hex results fail closed. All four SHA-256 call sites use the verified command object. The compiler remains exactly one invocation with no retry, and existing placement/output-containment guards are unchanged.

## Executed verification

- Builder parser checks: Windows PowerShell `5.1.26100.9549` `PASS`; PowerShell `7.6.5` `PASS`.
- Builder corrected focused/direct run: `62 PASS`.
- Final independent Tester parser checks: both shells `PASS`, zero parser errors.
- Final independent focused run: `30 PASS`, no skips. This included live command-path directory symlink/reparse rejection in both shells, clean and hostile `PSModulePath`, missing/invalid explicit module, trusted hash routing, one compiler invocation/no retry, and output/direct-drive-child containment.
- Final independent direct no-build regression: `44 PASS` for TASK-047 readiness-monitor and OBS runtime source contracts.
- `git diff --check`: `PASS`.
- Allowed-file scope: `PASS`.
- Final Critic: `ACCEPT`, Critical `0`, High `0`, Medium `0`, Low `1` parked outside scope.
- Final Tester: `ACCEPT / PASS`, Critical `0`, High `0`, Medium `0`, Low `0`.

The parked Critic Low is the historical TASK-042 test's comment-based legacy import assertion. Its file was outside the frozen Allowed Files; the dedicated TASK-104 tests execute the new resolver directly, so the Low does not weaken this unit's accepted claim.

An optional TASK-047 receipt-contract collection remained `NOT_CONFIRMED` because the existing Python environment lacked `jsonschema`; no dependency acquisition was authorized or attempted. It is not a failure of the corrected hashing path.

## Roots and intentional residuals

No build, installer, application, Resolve, release or deployment output root was created. Test-only roots are unique children of the system Temp root and are intentionally retained:

- `C:\Users\user\AppData\Local\Temp\task104-builder-32241a2d66d344a4877910910b358c30`
- `C:\Users\user\AppData\Local\Temp\task104-builder-b42f7874ec5744abb64b68b8e2ee3a0e`
- `C:\Users\user\AppData\Local\Temp\task104-builder-ff2baa0834a24ba98fabfa675bb0467a`
- `C:\Users\user\AppData\Local\Temp\task104-builder-fix-6e4a46be36f148f9b386651ceda18675`
- `C:\Users\user\AppData\Local\Temp\bvp-task104-tester-f794f4e45f8142d2b19e8c01b51976ac`
- `C:\Users\user\AppData\Local\Temp\bvp-task104-final-tester-c04b5ef031b949da9c158d5517fdeb9c`

The prior failed TASK-036/TASK-104-triggering partial build output remains untouched in its original TASK-036 worktree. Existing `C:\BVP-QA-471-*` historical directories were not read, written, deleted or reused.

## Gates and next action

No actual build or compiler invocation, installer, Product launch, Resolve action, paid/provider/private-media effect, Release, Deploy or Production effect occurred. A replacement build is not authorized by this unit. Push, pull request and merge were not inferred from implementation authority.

The next action is to commit the exact Allowed Files on `codex/task-104-powershell-hash-resolution`, preserve this Evidence externally at `C:\home\baisound\evidence\bai-video-production\TASK-104\powershell-hash-resolution\20261010-r01\`, read it back, and hand off publication as a separate gate.
