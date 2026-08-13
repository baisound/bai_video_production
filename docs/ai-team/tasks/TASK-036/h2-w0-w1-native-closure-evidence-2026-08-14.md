# TASK-036 — H2 W0/W1 Native Closure Evidence

- Date: `2026-08-14`
- Candidate: `0.20.1 / v0.20.1 / stable`
- Gate decision: `W0_PASS / W1_PASS / W2_PACKAGED_NATIVE_E2E_PASS`
- TASK decision: `MINIMUM_EDITING_PRODUCT_MVP_PASS`
- M3B: `PASS`

## Product corrections

- packaged startup preflight and native error presentation;
- actionable missing-WebView2 recovery without automatic install;
- explicit 166-character maximum executable-path policy;
- explicit EdgeChromium/WebView2 renderer selection;
- visible keyboard focus, skip navigation and semantic editing/timeline/button names;
- high-scale responsive layout below 900 CSS pixels;
- repeatable clean-profile/display/accessibility and WebView2-recovery Windows gates.

## Windows package and native Evidence

- OS: Windows 11 build `26200`
- Build runtime: Python `3.12.4`, PyInstaller `6.22.0`, pywebview `6.2.1`
- Final candidate executable SHA-256: `700acbe7384521a075779eddb173bd5e655e4752874195ae61da02ace612550a`
- Clean profile: package copied to a new temporary directory outside the checkout; prior app state false; native window opened; owned process exited.
- Displays: three real 1920x1080 monitors; all reported 96 DPI / 100%; the 1500x850 native window moved fully inside each monitor and remained usable.
- Accessibility: Windows Narrator session active during the smoke run; Windows UI Automation exposed 14 named controls including Project, Media, Save destination, Edit, Subtitle, Review, Export, CUT/KEEP and approval actions.
- Visual QA: native Shell rendered the expected NLE layout after foreground capture; no clipped top-level workflow actions were observed at the native test size.
- Missing WebView2: isolated with `WEBVIEW2_BROWSER_EXECUTABLE_FOLDER` pointing to an intentionally absent runtime. The installed host runtime was not removed or changed. The native dialog contained the stable error code, install/repair instruction and official WebView2 URL, then exited safely.
- Long path: the proven 166-character executable-path maximum is enforced before WebView startup and is covered by positive/negative automated tests. This replaces the previous unsupported 245-character crash boundary with an explicit support policy.
- Increased scale: 125%, 150% and 200%-equivalent viewport pressure is covered by the deterministic responsive contract; below 900 CSS pixels the three-column canvas becomes one column with scrollable timeline. The active Owner display settings were not mutated.

## Automated validation

- TASK-036 focused regression: `33 / 33 PASS` before the final responsive addition.
- Final full WSL2 Ubuntu regression after all Product and release-metadata changes: `810 / 810 PASS` in `47.24s`; `compileall` PASS.
- Windows clean-profile/display/UI Automation gate: `PASS`.
- Windows Narrator semantic-label smoke: `PASS`.
- Windows isolated missing-WebView2 recovery gate: `PASS`.
- Candidate one-dir PyInstaller build: `PASS`.

## Claim boundary

TASK-036 is complete for the Minimum Editing Product MVP defined by the canonical roadmap. This does not claim that every future GPU, display driver, accessibility tool, DPI topology or Windows release is certified. It also does not expand Resolve/Cubase ownership, paid-provider authority or Production-write authority.

## Exact release decision

The correction is backward-compatible startup/UX hardening after v0.20.0, so a patch version is correct. The exact decision is `0.20.1 / v0.20.1 / stable`. Tag and Release may be created only after PR merge and exact main SHA verification.
