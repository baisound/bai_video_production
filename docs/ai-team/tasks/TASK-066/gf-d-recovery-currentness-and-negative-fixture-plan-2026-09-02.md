# TASK-066 GF-D recovery currentness and negative fixture plan

- Audit date: `2026-09-02 JST`
- Scope: `GF-D / DbD compute-profile consumer only`
- Development profile: `DEV-4 FOUNDATION CRITICAL`
- Result: `RECOVERY_CANDIDATE_IDENTIFIED / SOURCE_AND_MERGE_EFFECT_PARKED`
- Authority created by this document: `false`

## 1. Frozen currentness

The canonical base used by this audit is:

- repository: `baisound/bai_video_production`
- remote main: `0de3d2ef026c2d7e21ce75ff395e4df3254530e4`
- remote-main post-merge CI run: `33565277937 / SUCCESS`
- audit branch: `codex/task-066-gf-d-recovery-audit`
- audit worktree: `C:\home\baisound\projects\bai-video-production\.worktrees\task-066-gf-d-recovery-audit`

The primary checkout was not used for mutation. It remains at
`3223e47c5e570b0bf1776ba53e4e7513f1eccb57`, is `722` commits behind the
locally resolved `origin/main`, and contains many unknown untracked paths.
Every unknown path is preserved. No reset, cleanup, move, staging or reuse was
performed.

## 2. PR #469 exact recovery state

Draft PR `#469`, `TASK-066: DbD計算プロファイルを安全側へ統合`, remains open at:

- branch: `codex/task-066-gf-d`
- head: `65bf18135debe36c25f53ac8d362b4e9dbff2fa8`
- merge base: `35cdf1ad475633dcf035e0616e979b5a8fde0c88`
- comparison to current main: `2 ahead / 40 behind / diverged`
- worktree readback: clean, tracking its origin branch
- current-main changes to the nine GF-D Allowed Files since the merge base:
  `0`

The nine PR paths are:

1. `packaging/task049_training_studio_windows_entry.py`
2. `packaging/task049_trivia_editor_windows_entry.py`
3. `src/ai_video_production/dbd_reasoning_local_runtime.py`
4. `src/ai_video_production/dbd_training_studio.py`
5. `src/ai_video_production/dbd_trivia_editor.py`
6. `tests/test_task049_dbd_training_studio_packaging.py`
7. `tests/test_task049_dbd_trivia_editor_packaging.py`
8. `tests/test_task054_dbd_reasoning_local_runtime.py`
9. `tests/test_task066_dbd_compute_profile.py`

The branch is therefore mechanically transplantable onto a fresh-main
successor without a direct target-path conflict. This observation is not a
merge authorization and does not replace a fresh semantic review.

### Hosted check interpretation

At the exact PR head:

- dependency audit: `PASS`
- secret scan: `PASS`
- Linux and Windows Python matrices: each reached the same one-test failure
- failing test:
  `tests/test_task051_r7a_source_gate.py::test_r7_training_studio_gate_uses_current_accepted_source`
- expected canonical text SHA-256:
  `d773bec235d38777e9c51be36433f776c1317346af6913f52b6b73aa585d3975`
- observed GF-D source SHA-256:
  `c7e5244b2a8c0ffcc4cdabc968986370db5aeb4f59bae99b624ce33bb77abd48`
- representative full hosted result:
  `5077 passed / 30 skipped / 1 failed / 11 subtests passed`
- Release metadata check: `FAIL` because the shared CHANGELOG/version closure
  is intentionally outside GF-D ownership

The single source-hash failure and the shared CHANGELOG failure are independent
cross-owner gates. GF-D must not repair either file directly.

## 3. Local focused rerun status

No new local PASS is claimed.

- normal `python`: unavailable on PATH
- bundled workspace Python: available, but contains no `pytest`
- WSL Ubuntu route: `Wsl/Service/E_ACCESSDENIED`
- dependency installation: not attempted
- native GUI, packaged EXE, real GPU execution and provider/model effects:
  `NOT_EXECUTED / NOT_CONFIRMED`

Historical branch evidence remains evidence only:

- GF-D focused suite: `115 PASS`
- follow-up focused suite: `53 PASS`
- local full suite: `5098 PASS / 9 SKIP / 1 source-hash failure`

## 4. Recovery rule

Do not rebase or force-push PR #469. The preferred bounded recovery is:

1. allocate the accepted-source hash Gate to its current exact owner;
2. allocate the shared CHANGELOG/version closure to its current exact owner;
3. create a fresh successor from current main;
4. transplant only commits
   `7457670a182a36ad3ee8695cd340ab0d8e0fc326` and
   `65bf18135debe36c25f53ac8d362b4e9dbff2fa8`;
5. verify the exact nine-path scope and re-review current GF-A contracts;
6. receive the hash-Gate and CHANGELOG heads without editing those paths in
   GF-D;
7. rerun focused, source-gate, relevant regression and hosted checks;
8. keep the successor Draft until Critical/High findings are `0/0`.

An owner may choose a non-force merge-forward of the existing branch instead,
but only after the same cross-owner gates and exact-head review. This document
does not authorize either route by itself.

## 5. Current authority-laundering boundary

Current main `desktop_compute_probe.py` exposes:

- public `RuntimeModuleEvidence` and `ProbeResult` dataclasses;
- public/exported `capability_from_probe_result`;
- module-visible `_LIVE_CAPABILITY_TOKENS` and its lock;
- a live-token check whose state exists inside the same importable Python
  process.

The frozen registry currently reports
`DISABLED_UNTIL_HELPER_SEALED`, so the public factory is effect-zero today.
That disabled row is an interim fail-closed state, not proof that the public
factory becomes Production authority after a future `SEALED` change.

The GF-D candidate does not import or call `capability_from_probe_result` and
does not launch a reasoning/training process from a public readback. Its
`DbDComputeProfileReadback` is data-only, always has
`authority_created=false`, keeps `reasoning_execution_authorized=false` and
`training_authorized=false`, rejects Tk GPU-rendering claims, makes model rows
non-selectable, and rejects `save_selection`.

This effect-zero behavior is mandatory until a separate cross-owner GF-A
correction supplies a trusted Product-process or OS-broker capability. Public
dataclasses, hashes, booleans, module tokens and public factories must never be
accepted as GF-D execution authority.

## 6. Future owner-partitioned negative fixtures

### 6.1 GF-A / trusted producer negatives

These belong to the exact owner of `desktop_compute_probe.py` and its tests.
GF-D must not add them by editing GF-A source directly.

1. `test_public_probe_dataclasses_cannot_mint_production_capability`
2. `test_public_factory_and_module_live_token_have_zero_authority`
3. `test_copy_replace_pickle_and_deserialization_cannot_recreate_capability`
4. `test_same_fields_without_actual_trusted_process_have_zero_authority`
5. `test_wrong_run_helper_backend_layout_profile_or_workload_is_rejected`
6. `test_production_rejects_injected_process_backend_attestor_or_test_clock`
7. `test_capability_enters_in_flight_once_and_burns_on_success`
8. `test_capability_burns_on_exception_and_cannot_be_reused`
9. `test_double_and_concurrent_consume_have_exactly_one_winner`
10. `test_restart_or_process_boundary_cannot_rehydrate_live_authority`

Every case must assert `Popen delta 0`, Product-setting delta `0`, diagnostic
body leak `0`, and no public receipt claiming authority.

### 6.2 GF-D consumer negatives

These are candidates for the existing GF-D test ownership after the producer
contract is canonical:

1. `test_gpu_required_without_private_capability_has_popen_zero_and_save_zero`
2. `test_public_profile_readback_remains_data_only_when_constructed_loaded`
3. `test_public_probe_result_or_public_adapter_capability_is_not_an_apply_input`
4. `test_wrong_operation_instance_layout_profile_revision_or_workload_has_zero_effect`
5. `test_copied_pickled_or_deserialized_capability_is_rejected_before_effect`
6. `test_double_concurrent_and_exception_reuse_have_zero_effect_after_first_entry`
7. `test_backend_change_between_prepare_launch_and_readback_fails_closed`
8. `test_cpu_explicit_never_runs_gpu_required_reasoning_or_training`
9. `test_trivia_cpu_control_plane_remains_available_without_gpu_authority`
10. `test_tk_frontend_never_claims_gpu_rendering`
11. `test_feature_local_model_selector_and_save_route_remain_absent`
12. `test_failure_diagnostic_is_bounded_body_free_and_path_free`

For all consumer negatives, assert separately:

- child-process launch delta: exact `0`
- feature-local model-selection write delta: exact `0`
- training/Dataset/Provider effect delta: exact `0`
- central compute-profile mutation delta: exact `0`
- unrelated-file overwrite/delete delta: exact `0`
- Tk GPU-rendering claim: `false`

The future positive path must accept only a private, one-use Product-operation
capability bound to the actual probe run, helper/build/backend identity,
InstallLayout, profile revision, workload, process/session and exact execution
budget. Method entry changes the capability to `IN_FLIGHT`; success and every
exception burn it. A new attempt requires a fresh trusted operation.

## 7. Direct dependency currentness

TASK-068 draft PR `#497` is open at
`516fc73d449ae8aa76845eaca3a2b193f5c5f6d1`:

- comparison to current main: `5 ahead / 2 behind / diverged`
- merge base: `354ea2534ad5739a099d9eeaf0f1da9a7210ddb6`
- current-main changes to its ten target paths since that merge base: `0`
- six hosted Python jobs: `PASS`
- dependency audit and secret scan: `PASS`
- Release metadata check: `FAIL`
- PR state: `OPEN / DRAFT / UNSTABLE`

TASK-068 therefore has no canonical-main completion receipt yet. Its source is
not changed by GF-D, and downstream TASK-063/060/061 corrective source work
remains parked until the required canonical receipt chain exists.

## 8. Effect ledger and next action

This audit performed:

- Product source mutation: `0`
- shared hash-Gate mutation: `0`
- CHANGELOG/shared metadata mutation: `0`
- process launch, model install/download, provider call: `0`
- Release, Deploy or Production Activation: `0`
- destructive cleanup/reset/force push: `0`

Next action is cross-owner receipt acquisition, not speculative source work:

1. obtain exact current owners and locks for the accepted-source hash Gate and
   CHANGELOG/version closure;
2. wait for TASK-068 canonical merge only for the dependent corrective queue;
3. after the two GF-D gates are available, create or approve one fresh-main
   successor candidate and run the owner-partitioned negative matrix;
4. do not elevate the current disabled/no-launch state to native or Production
   PASS.
