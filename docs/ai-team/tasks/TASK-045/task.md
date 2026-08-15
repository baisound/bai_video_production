# TASK-045 — V6 Native Acceptance / Compatibility / Release Closure

## Identity

- Priority: `OWNER_MAXIMUM / RELEASE_CLOSURE`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`
- Status: `ACTIVE / FULL_DESIGN_AND_CRITIC_LOCAL_PASS / HOSTED_PENDING`
- Depends on: TASK-043, TASK-042 P-V6-4 and TASK-044

## Goal

Prove that the integrated V6 Product opens supported old projects, safely plans
or rejects incompatible migrations, recovers interrupted edits/jobs, supports
the required native Windows interaction and accessibility routes, and can be
released without claims broader than Evidence.

## Acceptance

- supported-version migration round trip and backup restore;
- corrupt/unknown/newer format fail-closed behavior;
- 2h+ Timeline and large Asset Library performance budget;
- keyboard, Narrator, multi-monitor/DPI and native file-picker regression;
- real local editing and bounded Export Queue acceptance;
- full regression, build, clean-install and conversation-free restart;
- exact SemVer decision, PR/main merge, exact merge SHA, annotated Tag and GitHub
  Release only after all required gates pass.

Paid Provider, TASK-013 Native H3 replay and Production Deploy are not release
requirements and remain separate Human Gates.

## Current execution plan

1. `P-RC-1`: compatibility corpus, explicit legacy discovery, registered
   lossless copy-on-write migration, backup/restore roundtrip and bounded Asset
   paging.
2. `P-RC-2`: two-hour/large-library performance, integrated packaged Windows,
   clean-install and conversation-free restart acceptance; exact SemVer decision.
3. `P-RC-3`: release metadata branch/PR, main merge, exact SHA, annotated Tag and
   verified GitHub Release.

The current-main audit baseline is exact main
`6703c42a3aa06a563071f1a48dc7aab113f4dfe4`; PR #72 passed `9 / 9` and TASK-044
is hosted-closed. Existing compatibility/recovery/NLE focused tests pass `94 / 94`.
Detailed design and two Critic rounds close at unresolved Critical/High `0 / 0`.
Implementation starts only after this design checkpoint is hosted-closed and
fresh-main P-RC-1 is reselected.

