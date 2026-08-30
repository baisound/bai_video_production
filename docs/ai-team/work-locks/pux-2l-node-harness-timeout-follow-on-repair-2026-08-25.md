# P-UX-2L Node Harness Timeout Follow-on Repair

Date: `2026-08-25`
State: `BOUNDED_TEST_HARNESS_REPAIR`

## Trigger

- main commit: `f7ecb044a70211ff0283e53c743c860676d8c0b6`
- CI run: `32858850488`
- failing job: `97837503130` (`windows-latest`, Python 3.13)
- failing test: `tests/test_task036_v611_interaction_contract.py::test_subtitle_and_cut_single_flight_route_behaves_fail_closed_in_node`
- observed result: the Node subprocess exceeded its fixed 30-second timeout by about 0.38 seconds under a contended xdist worker
- surrounding result: 3784 passed, 5 skipped, one timeout failure

## Classification

The JavaScript contract did not report an assertion or Product behavior failure. The bounded subprocess wrapper terminated before the hosted runner scheduled the short Node contract to completion. A prior repair raised the original 10-second boundary to 30 seconds; this run is exact evidence that the new boundary remains too close to observed Windows contention.

## Repair

- change only `NODE_BEHAVIORAL_CONTRACT_TIMEOUT_SECONDS` from 30 to 90
- retain the outer pytest timeout of 120 seconds
- retain `check=False`, captured output, return-code assertion, exact `OK` stdout assertion and every JavaScript assertion
- do not change Product source, workflow parallelism, xdist worker count or retry policy

## Boundaries

- no Product source change
- no workflow change or CI weakening
- no CHANGELOG or lock-registry change
- no TASK-029 R8 implementation, schema, test or canonical document change
- no Provider, media, native application, Release or Deploy effect
- no retry of the failed unchanged main head

## Acceptance

- focused Node behavioral contract passes locally
- interaction contract test file passes locally
- hosted CI passes all six matrix jobs, including Windows Python 3.13
- Security and release metadata checks pass; post-merge main CI and Security pass before TASK-029 R8 resumes
