# TASK-051 R7B — Missing Gate Test File Recovery

Governance: `DEV-3 HIGH ASSURANCE`
Status: `BOUNDED_FIX_RETEST`

## Failure classification

The R7A installer correctly updated the accepted-source hash and successfully installed the
R7 governance files, runner, launcher, and R7A correction document. It then attempted to run:

`tests/test_task051_r7a_source_gate.py`

but that file was not included in the installer's `ADD` tuple.

Therefore the real worktree was left in a safe, partially-installed R7 state. No Product source
was modified by this failure.

## Corrective action

R7B adds only the missing test file to the installer's `ADD` set. Existing R7 files are handled
idempotently (`SKIP same`) and are not rewritten when their contents already match.

## Retest

The installer reruns:
- R7 acceptance-gate definition test;
- R7A accepted-source hash test;
- runner/launcher py_compile;
- git diff --check.

After R7B gate installation passes, run the unchanged R7 acceptance command.

No unresolved HIGH finding remains in R7B scope.
