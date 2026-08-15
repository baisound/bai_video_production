# TASK-045 — V6 Native Acceptance / Compatibility / Release Closure

## Identity

- Priority: `OWNER_MAXIMUM / RELEASE_CLOSURE`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`
- Status: `FORMAL_RELEASE_COMPLETE / V0_21_0_RELEASED / POST_RELEASE_SYNC_HOSTED_CLOSED`
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

The stable `v0.21.0` release is not reopened by future OBS work. Any release
that later includes P-OBS-1 must independently prove the exact supported OBS
build/ABI/load/callback, Plugin/Core IPC separation, 48 kHz/24-bit/mono capture,
device/drop/crash/restart behavior, private-data containment, GPL/source/
notice/signing/distribution decision and clean install/upgrade/rollback. A
P-OBS-0 path discovery or P-OBS-1 local test is not a Release authorization.

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
Design PR #74 passed hosted `9 / 9`, merged at exact main
`1ddc8ea39e45ee62590a443e3a67d8bb901b6062`, and completed branch/checkout
cleanup. At the P-RC-1 local checkpoint, focused `100 / 100` and full WSL2
`1123 / 1123` passed; its hosted closure is recorded immediately below.

P-RC-1 PR #75 passed hosted `9 / 9`, merged at exact main `402c8956a5f5f3ac485c43db2b3e35e667846a88`, and completed cleanup. P-RC-2 packaged Project/native/restart/clean-install acceptance passes with full Windows `1123 passed, 1 expected skip` and WSL2 `1124 / 1124`; PR #76 final head `76644790b8e154014af7e46b5efeef49b3d58789` then passed hosted `9 / 9`, merged at exact main `84837e34a42234e23a544f54c8fe0c49aab8cacb`, and completed cleanup. Exact decision is `0.21.0 / v0.21.0 / stable`; P-RC-3 publication closure is recorded below.

P-RC-3 PR #77 final head `c5cdff27e7c0918efa37876c064dcfd5a3deae76`
passed hosted `9 / 9`, merged at exact release-code main
`c38187ed54e3601c44411d9b8a128348b0d8a7b7`, and completed the release branch
and checkout cleanup. Annotated Tag `v0.21.0`, Release workflow `31858212510`,
stable GitHub Release, published wheel/sdist digest verification and a fresh
published-wheel install all pass. This final docs-only post-release Evidence
sync does not reopen Product code or authorize Production Deploy.

