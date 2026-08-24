# P-UX-2L Transcription Process Timeout Repair

Date: `2026-08-25`
Profile: `DEV-3`
State: `LOCAL_TECHNICAL_GO_PENDING_HOSTED`

## Trigger

P-UX-2L CHANGELOG lock closure merge `aaf433ebe0e087a07f173fdf7ec99994b4c5fe0e`
started post-main CI run `32774384916`. Five of six matrix jobs passed. Windows
Python 3.12 job `97581951938` failed only in
`test_cross_process_admission_executes_provider_exactly_once` because a spawned
process remained active when the parent used the test-local fixed
`process.join(10)` completion wait.

The failed run completed the remaining suite with `3759 passed`, `5 skipped`,
and one failure. Windows Python 3.11 and 3.13, and all Ubuntu jobs, passed. The
corresponding post-main Security run `32774384866` passed.

## Detailed Design

- Introduce named test-local constants
  `PROCESS_COMPLETION_TIMEOUT_SECONDS = 30` and
  `PROCESS_CLEANUP_TIMEOUT_SECONDS = 5`.
- Use the completion constant only for the spawned-process join in the exact
  cross-process admission test.
- On every exit path, recover any live child with bounded
  `terminate -> join -> kill -> join` cleanup and require that no child remains
  alive. A process that exceeds the completion wait remains an explicit failure.
- Preserve the admission barrier, provider behavior, process count, provider
  exact-once assertion, result states, and marker assertion unchanged.
- Preserve the workflow-wide pytest timeout of 120 seconds.
- Do not modify Product source, workflow files, provider execution, transcript
  output, locks, CHANGELOG, or canonical Product truth.

This change increases observation time for a valid Windows spawn lifecycle. It
does not convert a live process into success: after the bounded wait the test
still requires the child to be stopped and `process.exitcode == 0`. A hung,
failed, or incomplete child is reclaimed and remains a failure.

## Verification Contract

Required before merge:

1. focused repeated execution of the cross-process admission test;
2. the complete local-transcription-operation test module;
3. relevant TASK-036 regression;
4. independent Tester, Critic, and Judge with unresolved Critical/High findings
   equal to zero;
5. hosted checks across all six OS/Python matrix jobs, release metadata, and
   Security;
6. post-main CI and Security read-back before the lock-release notification.

## Local Verification and Independent Review

- Builder focused execution: one initial PASS plus four parallel PASS; the
  pre-cleanup parallel maximum observed duration was 9.04 seconds.
- Builder module execution: `22 / 22 PASS`.
- Builder related TASK-036 execution after cleanup fix: `70 / 70 PASS`.
- Independent Tester: `PASS`, including cleanup failure-path fault injection,
  terminate/kill fallback verification, four parallel real-process PASS, and
  `70 / 70` related regression.
- Independent Critic: initial Medium finding for missing timeout cleanup; fix
  cycle 1 closed the finding and final verdict is `Technical GO`.
- Independent Judge: `CONDITIONAL MERGE GO`.
- Final unresolved findings: `C/H/M/L = 0/0/0/0`.
- Remaining gates: fresh-main drift check, hosted checks, normal merge, and
  post-main CI/Security read-back.


## Authority and Safety

This is a test-harness timing repair only. It creates no provider, native,
media, deployment, release, or Production authority. No paid or external
provider call is authorized or executed by this repair.
