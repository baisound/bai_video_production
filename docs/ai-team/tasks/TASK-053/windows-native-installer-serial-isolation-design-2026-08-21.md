# TASK-053 R1 Windows native installer serial isolation

Date: 2026-08-21
Status: DEV-2 IMPLEMENTED / HOSTED ACCEPTANCE PENDING

## Trigger and scope

PR #213 changed only governance documents, but its Windows Python 3.12 CI run
lost one xdist worker while executing
`tests/test_task047_obs_installer_contract.py::test_installer_executes_clean_repair_collision_and_uninstall`.
The worker had already run for more than six minutes. The same base and Product
tests passed on other recent PRs, so this is a native-installer isolation defect,
not Evidence that the TASK-014 document change broke Product code.

This corrective remains inside TASK-053's CI test-execution responsibility. It
does not change TASK-047 installer behavior, Product source, version,
CHANGELOG, packaging bytes, Provider behavior, or release authority.

## Design

- Linux keeps the existing complete two-worker `loadfile` suite unchanged.
- Windows keeps the same complete suite except that the entire TASK-047
  installer contract file is omitted from the xdist invocation.
- The same Windows matrix job then executes that exact file once in a dedicated
  serial pytest process.
- Static installer checks and the Windows-only clean/repair/collision/uninstall
  acceptance therefore still run on Python 3.11, 3.12, and 3.13.
- The serial process retains pytest-timeout and slow-duration diagnostics but
  has no xdist worker, worker restart, or replay surface.
- The existing 20-minute job timeout, compileall step, OS/Python matrix, FFmpeg
  verification, and ephemeral CI-only tooling remain unchanged.

The serial item receives a 300-second per-test timeout. This is bounded above
the prior generic 120-second threshold because it builds a fake OBS executable
and runs real Inno clean install, repair, collision, and uninstall operations.
Timeout is still a hard failure; the workflow does not skip, deselect, retry,
or convert a native failure to PASS.

## Acceptance

- workflow contract proves Linux remains unfiltered;
- workflow contract proves Windows excludes the file only from xdist and runs
  it exactly once serially;
- no `--deselect`, skip marker, retry, or worker restart is added;
- focused contract and related TASK-047 static tests pass locally;
- `git diff --check` and YAML parse/read pass;
- hosted Windows 3.11/3.12/3.13 and Ubuntu 3.11/3.12/3.13 all pass before merge.

The actual Inno acceptance remains a Windows hosted/native observation. Linux
will continue to report its existing intentional Windows-only skip.
