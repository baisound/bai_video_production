# TASK-045 P-RC-2 Acceptance Plan and Evidence

Date: 2026-08-15
Authority: `BVP-TASK-045-P-RC-2 / ACCEPTANCE`
State: `LOCAL_PASS / HOSTED_PENDING`

## Fresh-main selection

- P-RC-1 PR #75 exact head: `30b20deb09f26c27ef98b0518953748fdc4c9c0f`;
- hosted checks: `9 / 9 PASS`;
- exact main after merge: `402c8956a5f5f3ac485c43db2b3e35e667846a88`;
- P-RC-1 remote branch and dedicated checkout cleanup: `PASS`;
- fresh branch: `refactor/task-045-prc2-native-acceptance`.

The current checkout is the Implementation Source of Truth. Stable formal
Release remains `v0.20.1`; this document records the exact next SemVer only after
the completed acceptance matrix below.

## Acceptance plan

1. measure a two-hour-plus, 10,000-clip controller projection with seven samples;
2. build the exact fresh-main Windows one-dir package;
3. run clean-profile Narrator/UIA and three-display acceptance;
4. run semantic Timeline zoom/scroll and native picker cancellation;
5. close the owned process, relaunch the same copied package and isolated profile
   without conversation context, and revalidate the semantic controls;
6. run focused/full Windows and WSL2 regression, compileall, wheel/build and clean
   install;
7. record exact SemVer decision only after every independent gate closes.

No Provider, paid operation, credential input, Resolve/Cubase mutation, TASK-013
native replay, Tag, GitHub Release or Production Deploy is authorized in P-RC-2.

## Evidence checkpoint 1

- Windows Python `3.12.4`, PyInstaller `6.22.0` and required build dependencies:
  `PASS`;
- exact-main one-dir build: `PASS`;
- initial pre-corrective packaged EXE SHA-256:
  `8d7f9247c2fb5ba7f5d67578ac2fc43579f07374e09859a73f214ab5d00e3275`;
- checkout-external clean profile: `PASS`;
- UIA semantic buttons: `36`, unnamed `0` among accepted buttons;
- Narrator session: `ACTIVE_DURING_GATE / OWNED_START_STOP`;
- displays: `DISPLAY1`, `DISPLAY2`, `DISPLAY3`, move/on-target `3 / 3 PASS`;
- observed DPI: `96 / 100%` on all three current displays;
- screenshot: `PASS`;
- owned packaged process exit: `PASS`.

## Evidence checkpoint 2

- two-hour-plus / 10,000-clip controller acceptance: `PASS`;
- WSL2 P-RC focused tests: `14 / 14 PASS`;
- packaged semantic controls: `36`, unnamed buttons `0`;
- packaged zoom and horizontal scroll geometry changes: `PASS`;
- native media picker cancel without Product exit: `PASS`;
- same-package, same-isolated-profile conversation-free restart: `PASS`;
- profile entries reused on restart: `84`;
- Provider/paid/Resolve/Cubase execution: `false / false / false / false`;
- wheel clean install into a newly created Windows venv: `PASS`;
- installed distribution/package version: `0.20.1 / 0.20.1`;
- `pip check`: `PASS`;
- initial pre-corrective wheel SHA-256:
  `cbf13d850288f8bd0cffc40ed831447c84a5950c2576f35a130729aab638ef6e`;
- full Windows clean-install regression: `1123 passed, 1 expected skip`;
- full WSL2 regression: `1124 / 1124 PASS`;
- Windows compileall: `PASS`.

## Observed native corrective 1

The first packaged synthetic Project launch exposed a pywebview API-discovery
recursion through the public `pre_edit_runtime` object graph and its rational
Timeline rate. This is an observed integrated Product defect, not a fixture
failure. The bounded correction makes every rich service/runtime/application
reference on `Task036ShellBridge` private, retaining only the existing typed
allowlisted bridge methods as the public JavaScript surface. Tests now reject all
nineteen public internal attributes. No Provider/native execution authority is
added.

## Final candidate Evidence

- corrective focused Windows: `51 / 51 PASS`;
- corrective focused WSL2: `51 / 51 PASS`;
- final packaged EXE SHA-256:
  `9d8a8f367d674db8c5c21d249fbf6f33c7dfea2142ff90889cc6e55998f05408`;
- final one-dir build: `PASS`;
- final clean-profile/Narrator/UIA: `PASS`, semantic buttons `36`, unnamed `0`;
- final display movement: `DISPLAY1/2/3`, `3 / 3 PASS`, observed `96 DPI / 100%`;
- final default Timeline zoom/scroll and native picker cancel: `PASS`;
- final default conversation-free restart with `84` reused isolated-profile
  entries: `PASS`;
- owned synthetic v0.20.1 Project packaged open/reopen: `PASS`, semantic buttons
  `31`, unnamed `0`, reused isolated-profile entries `50`;
- synthetic Project manifest file SHA-256 before/after:
  `9c090377a055d28d726338410a18bd56a35f6d41a5c86bef8dd48fb5c306313e` /
  exact same value;
- pywebview API-discovery recursion after corrective: `NOT_REPRODUCED`;
- final corrective wheel clean install and `pip check`: `PASS`;
- final wheel SHA-256:
  `d17e41accd294093a8ed731d50dd66dab8c8743bfc6b27bdd3e8a0f216b91fb7`;
- final full Windows regression: `1123 passed, 1 expected skip` in `72.11 s`;
- final full WSL2 regression: `1124 / 1124 PASS` in `55.74 s`;
- final Windows compileall: `PASS`;
- Provider/paid/Resolve/Cubase execution: `false / false / false / false`.

## Exact release decision

- latest formal Release/Tag reverified: `0.20.1 / v0.20.1 / stable`;
- `v0.21.0` Tag/Release collision: `NONE`;
- actual impact: backward-readable additive Project migration application,
  Asset paging API/schema v3 index, packaged compatibility acceptance and a
  private-bridge corrective; no incompatible public contract removal;
- SemVer class: `MINOR`;
- exact decision: `0.21.0 / v0.21.0 / stable`;
- P-RC-3 authority: `CONDITIONALLY_AUTHORIZED_AFTER_P_RC_2_HOSTED_CLOSURE`;
- Production Deploy: `BLOCKED / NOT_PART_OF_RELEASE`.

## Hosted CI corrective

PR #76 initial head `b27f7bd4fb1a5b1e2e40a9a19fc490d66ea7f26f` passed
release-metadata and both security jobs, but all six OS/Python test jobs rejected
one canonical-document contract: `Development Candidate` must contain a plain
SemVer, not the combined version/Tag/channel decision. `PROJECT.md` and
`docs/ai-team/current-state.md` now retain `0.21.0` in that field and record
`0.21.0 / v0.21.0 / stable` separately. Post-corrective full WSL2 regression is
`1124 / 1124 PASS`. Hosted rerun remains required before merge.

## Final Critic / Judge

- native Evidence is bound to one exact final EXE checksum and separated from
  hosted CI Evidence;
- Project open/reopen uses only an owned synthetic fixture and changes no Human
  Project;
- the observed rich-object pywebview exposure is closed for all nineteen
  internal Bridge bindings, not only the initially failing runtime;
- performance claims remain bounded to seven-sample medians and the accepted
  Windows/WSL2 environments;
- unknown/lossy/ambiguous migration, paid Provider, credential input, native H3
  replay, Resolve/Cubase mutation and Production Deploy remain blocked;
- unresolved Critical/High: `0 / 0`.

Judge decision: `P_RC_2_LOCAL_PASS / HOSTED_CI_REQUIRED`. P-RC-3 begins only
after this branch passes hosted CI, merges to exact main, and completes remote
branch and dedicated checkout cleanup.
