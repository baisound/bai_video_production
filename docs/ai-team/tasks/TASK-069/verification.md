# TASK-069 FB-R1 verification

## Scope

FB-R1 is limited to root-bound reads of owner, import journal, receipt, pending,
and correlation artifacts.  It does not alter the delivery snapshot route,
publication/cleanup/CAS semantics, or Profile operations.

`SecureAuthorityIO` has a public 1 MiB ceiling.  The affected authority reads
therefore use the lesser of the caller bound and 1 MiB; a public receipt larger
than that ceiling is rejected rather than sent through a legacy path.  The
existing 4 MiB delivery and Profile routes remain explicitly marked
`legacy_compatibility=True` pending a separately authorized foundation/API
extension.

## Executed evidence

- `tests/test_task069_montage_learning_production_safety.py`: 10 passed.
- That suite plus `tests/test_task058_montage_learning_file_bridge.py`: 42 passed.
- `tests/test_task058_montage_learning_bridge_contracts.py`
  and `tests/test_task058_montage_learning_adapter_e2e.py`: 85 passed.
- All runs used Python 3.13 with bytecode and pytest cache disabled, and an
  owned non-drive-root `--basetemp` under this task worktree.

The owned, untracked `.pytest-task069-fbr*` directories remain under this
task's dedicated worktree as reproducible local test remnants.  No root-drive,
installer, native, provider, Release, Deploy, or Production effect occurred.

## Remaining Task-069 units

- Delivery and Profile reads require a public TASK-068-capable bounded read
  contract before their 4 MiB route can be replaced.
- FB-C, FB-P, FB-X, FB-PR, PRIV, and READY remain unstarted and require their
  separately scoped DEV-4 matrices.
