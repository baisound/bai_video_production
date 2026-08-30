# TASK-036 Local Transcription Thread Timeout Repair

Date: `2026-08-26`
Profile: `DEV-2 STANDARD`
State: `IMPLEMENTED_PENDING_HOSTED`

## Trigger

TASK-054 R6B-B PR `#379` CI run `32953458548` passed five of six matrix jobs.
Only Windows Python 3.12 failed in
`test_cross_instance_admission_executes_provider_exactly_once` after a worker
thread exceeded the test-local `thread.join(5)` boundary by about 0.78 seconds.
The same unchanged test passed on Windows Python 3.11 and 3.13, and the failed
job completed the remaining suite with `4105 passed` and `5 skipped`.

## Repair

- Replace the cross-instance fixture's fixed five-second completion wait with a
  named 30-second thread completion timeout.
- Preserve provider release, exact-once admission, result and recovery
  assertions unchanged.
- Keep a live thread after the bounded wait as an explicit test failure.
- Do not modify Product source, workflows, CHANGELOG, the integration-lock
  registry, provider behavior, or TASK-054 implementation.

This repair increases observation time for a valid Windows runner lifecycle. It
does not hide deadlock or incomplete execution because the fixture still
requires every thread to stop before evaluating the exact-once result.

## Verification Contract

1. Repeat the exact cross-instance fixture.
2. Run the complete local-transcription-operation test module.
3. Run the relevant TASK-036 regression required by the current CI repair gate.
4. Require hosted CI and Security PASS on the exact repair head.

## Authority Boundary

This is a test-harness timing repair only. It creates no Product, provider,
media, native execution, Release, Deploy, or Production authority and does not
acquire or alter the active TASK-054 shared CHANGELOG lock.
