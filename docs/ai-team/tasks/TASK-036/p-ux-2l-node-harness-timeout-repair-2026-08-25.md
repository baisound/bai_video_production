# P-UX-2L Node Harness Timeout Repair

Date: 2026-08-25
Task: TASK-036 / P-UX-2L
Governance: DEV-3 HIGH ASSURANCE
State: LOCAL TECHNICAL PASS / HOSTED PENDING

## Fresh-main checkpoint

- Integrated origin/main: `ed597b8c351ae550016f59fd21fd09f8b45cef6c`.
- Fresh-main merge: `d442b5b086163dbb19aa4105b3bfaa1ff70f62fe`.
- Reviewed test blob: `0c00ed72b2d92aaf040d48dc4a2c1b83e931a23d`.
- Pre-checkpoint exact target-path drift after merge: 0/2; this Evidence update only adds the fresh-main checkpoint.
- Fresh-main Node boundary: 10/10 PASS; related contracts: 67/67 PASS.

## Trigger

P-UX-2L target PR #306 merged at `0197c0c7ac1428a19bd08261fd410baa63675632` after 9/9 hosted checks passed. Its post-main CI run `32767840161` passed five matrix jobs but failed Windows Python 3.12 job `97561246853` because `test_subtitle_and_cut_single_flight_route_behaves_fail_closed_in_node` exceeded its bounded 10-second Node subprocess timeout. Post-main Security run `32767840260` passed.

No unchanged-head retry was used. The CHANGELOG integration lock remains nonclosed until a repaired main passes post-main CI and Security.

## Failure classification

The behavioral assertions did not fail. The same test passed on Ubuntu 3.11/3.12/3.13 and Windows 3.11/3.13, and the pre-merge PR matrix was green. Under the failing Windows 3.12 xdist job, Python observed `subprocess.TimeoutExpired` at the 10-second boundary. The log does not prove whether contention occurred before Node startup or during execution.

The embedded script has no timer, socket, MessagePort, stdin read, or child process. Its one deliberately pending Promise is explicitly resolved before the final assertions. No concrete dangling handle is identified, so this repair does not add forced process termination that could hide a future handle leak.

Product logic failure is `NOT_CONFIRMED`. This repair targets test-process lifecycle timing only.

## Detailed repair design

- Raise only this Node subprocess timeout from 10 to 30 seconds through a named test-local constant.
- Keep the repository pytest timeout at 120 seconds, skip condition, behavioral assertions, natural Node lifecycle, JavaScript extracted from Product HTML, and Product source unchanged.
- The 30-second boundary is one quarter of the outer pytest timeout and remains a bounded hang detector.
- Do not add forced `process.exit`, serial isolation, retry, sleep, or workflow weakening in this Atomic Unit.

This absorbs bounded Node startup, antivirus, and worker-scheduling contention while retaining natural teardown so a real dangling-handle regression still fails closed.

## Local verification

- Repaired Node boundary test: 50/50 consecutive PASS on Windows.
- `tests/test_task036_v611_interaction_contract.py`, `tests/test_task036_element_contract.py`, and `tests/test_task036_v611_visual_contract.py`: 67 PASS.
- Python compile of the modified test: PASS.
- Embedded Node syntax and behavior: exercised by the 50 repeated test executions and PASS.
- `git diff --check`: PASS.
- Hosted-equivalent local xdist command: `NOT_CONFIRMED` because the local environment does not include the pytest-xdist/pytest-timeout plugins; Hosted CI remains the authority for that matrix.

No Provider, paid service, model download, media, Resolve, native application, installation, release, deployment, or Product runtime side effect occurred.

## Independent review

- Tester: LOCAL TECHNICAL PASS; independent Node 10/10 and related 67/67 PASS.
- Critic: TECHNICAL GO on the final timeout-only design; the discarded forced-exit High finding is resolved.
- Judge: CONDITIONAL TECHNICAL GO; fresh-main and Hosted gates remain.
- Current unresolved findings against the final design: Critical 0 / High 0 / Medium 0 / Low 0.

## Remaining gates

- Independent Tester/Critic/Judge local review: complete with C/H/M/L 0/0/0/0.
- Repair PR hosted six-platform matrix, Security, and release-metadata checks: pending.
- Repair merge and fresh-main CI/Security read-back: pending.
- Existing P-UX-2L CHANGELOG lock closure/release: blocked until the repaired fresh main is green.
