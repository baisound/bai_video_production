# TASK-045 — V6 Native Acceptance / Compatibility / Release Closure

## Identity

- Priority: `OWNER_MAXIMUM / RELEASE_CLOSURE`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`
- Status: `ALLOCATED / DEPENDENCY_WAIT`
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

