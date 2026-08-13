# BAI Video Production v0.20.0 — Release Notes

- Channel: `stable`
- Release state: `CANDIDATE / MAIN_MERGE_TAG_RELEASE_PENDING`
- Exact decision: `0.20.0 / v0.20.0`

## Included

- TASK-007 human-reviewed CUT/KEEP planning with explicit final approval;
- TASK-010 real Resolve assembly on an exact Automation-owned `BAI_AUTO_*` Timeline, including linked A/V, source-rate conversion, edit-aware subtitles and idempotency/conflict protection;
- TASK-011 real Resolve render plus artifact video/audio/duration/LUFS/true-peak QA;
- TASK-012 deterministic atomic `EDITOR_WORK_*` handoff and real Cubase 13 stereo 48 kHz 24-bit PCM round-trip;
- TASK-036 packaged Windows W2 route: Project, media ingest, cached network-free local FasterWhisper, Subtitle, Cut Review, approval, Resolve apply, Render QA and atomic EDITOR_WORK in one Shell session;
- private trusted launch configuration, exact one-shot native-render authorization and frozen local ASR runtime dependencies;
- failure recovery that preflights optional handoff inputs and prevents publication of partial canonical EDITOR_WORK output.

## Verified

- Consumer WSL2 Ubuntu full regression after release metadata finalization: `805 / 805 PASS`;
- focused atomic handoff/launcher/runtime: `25 / 25 PASS`;
- Windows packaged W2 native E2E: PASS;
- post-W2 conversation-free restart: PASS;
- final Pilot Context Cost: `11,888` estimated tokens, `50.91%` below the W2 checkpoint;
- PR #20 hosted matrix: nine checks PASS before the release metadata commit; a fresh all-green run remains required for final merge.

## Required environment and known limitations

- Microsoft Edge WebView2 Runtime must already be installed; missing-runtime recovery is not validated;
- use a normal local install path. Executable path length `166` passed; length `245` failed because a packaged internal DLL path exceeded the Windows path limit;
- evidenced desktop viewports are single-monitor `1600x900` and `1366x768`;
- clean-profile startup, full DPI/mixed-monitor coverage and Windows screen-reader compatibility remain unvalidated and are parked to Phase H2;
- no claim is made for production/human-owned Resolve or Cubase project mutation outside the bounded, explicitly authorized workflow.

## Claim boundary

This release claims TASK-010/011/012 backend native PASS and TASK-036 W2 `SHELL_INTEGRATED / PACKAGED_NATIVE_E2E_PASS` only for the evidenced bounded environment. It does not claim overall TASK-036 `NATIVE_VALIDATED`, `DESKTOP_SHELL_NATIVE_UX_PASS`, `MINIMUM_EDITING_PRODUCT_MVP_PASS` or M3B completion.
