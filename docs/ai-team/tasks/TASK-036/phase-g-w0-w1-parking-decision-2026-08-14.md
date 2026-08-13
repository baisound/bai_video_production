# TASK-036 — Phase G W0/W1 Parking Decision

- Date: `2026-08-14`
- Consumer HEAD: `77a2cc9bd4ea1fa17d489d6523367f5a8171a35b`
- Decision: `W0_W1_REMAINDER_FORMALLY_PARKED_TO_PHASE_H2`
- W2: `PACKAGED_NATIVE_E2E_PASS`
- TASK-036 overall completion: **NOT CLAIMED**

## Why parking is correct

The current Windows machine proved packaged launch, WebView2 operation, native chooser reachability, focus return, Unicode paths, normal process cleanup and the full W2 editing route. The remaining cases require destructive or environment-changing setup that is independent of the accepted editing route:

- a disposable clean Windows user profile;
- removal or isolation of the installed WebView2 Runtime;
- 100/125/150/200% DPI and mixed-monitor hardware coverage;
- a Windows screen-reader session;
- packaging or bootstrap work for very long install paths.

These cases do not invalidate W2, but they prevent a claim that TASK-036 as a whole is complete. Balanced Execution therefore parks them to Phase H2 instead of repeating the accepted W2 route.

## Bounded release support

Until the parked cases pass:

- WebView2 Runtime is a required installed prerequisite; missing-runtime recovery is unsupported and unclaimed;
- use a normal local install directory; the executable path was proven at length `166`, while length `245` failed because a packaged internal DLL path exceeded the Windows path limit;
- Unicode install paths are supported within the tested short-path boundary;
- single-monitor `1600x900` and `1366x768` use is evidenced; the complete DPI/mixed-monitor matrix is not claimed;
- visible keyboard focus and non-color-only status are evidenced; screen-reader compatibility is not claimed.

This is a release-scope limitation, not a PASS result for the parked cases. It must be stated in release notes if the exact release decision authorizes a release before H2 closes them.

## H2 assignments and resume conditions

| Parked case | Resume condition | Required Evidence |
|---|---|---|
| clean-profile startup | disposable Windows user/profile is available | first launch with no developer checkout or prior app state |
| missing WebView2 | isolated disposable runtime environment is available | actionable recovery/bootstrap behavior without opaque crash |
| full DPI/mixed monitor | required scaling and monitor topology are available | usable layout, dialog placement and focus at each matrix point |
| screen reader | Windows accessibility test session is available | semantic navigation/status smoke report |
| long install path | bootstrap/path mitigation is designed | explicit enforced install policy or launch beyond the prior failure point |

## Claims after this decision

- W0: `PARTIAL / REMAINDER_PARKED_TO_H2`
- W1: `PARTIAL / REMAINDER_PARKED_TO_H2`
- W2: `PACKAGED_NATIVE_E2E_PASS`
- `NATIVE_VALIDATED`: not claimed for overall TASK-036
- `DESKTOP_SHELL_NATIVE_UX_PASS`: not claimed
- `MINIMUM_EDITING_PRODUCT_MVP_PASS`: not claimed

The next Phase G unit is post-W2 conversation-free restart Evidence followed by the final Pilot Context Cost and exact release decision.

## Evidence

- `evidence/native/phase-g-task036-packaging-20260813-01/task036-w0-w1-evidence.json`
- `evidence/native/phase-g-task036-w2-runtime-20260813-01/task036-w2-packaged-native-e2e.json`
- `evidence/native/phase-g-task036-w0-w1-parking-20260814-01/task036-w0-w1-parking-decision.json`
