# TASK-006 — UI Interaction Corrective Design v0.16.3

## Trigger Evidence

Windows acceptance exposed three usability defects in the Subtitle Workspace: the native dialog could open behind a fullscreen window on the primary monitor, relative insertion reused neighboring boundary timestamps instead of occupying the visible interior gap, and SRT export lacked conspicuous completion Evidence. A stale page after local-server shutdown could also make actions appear non-responsive.

## Corrective Contract

1. **Native dialog ownership** — capture `GetForegroundWindow()` at explicit operator launch and pass that HWND as the `IWin32Window` owner. If Windows yields no foreground HWND, use a temporary top-most owner. No remote filesystem exposure is introduced.
2. **Relative insert semantics** — `before`/`after` timing is computed by the backend, not by browser index arithmetic. Between left end `L` and right start `R`, use `L+1` through `R-1`. Reject the operation if that strict interior cannot represent a positive-duration cue. Before the first cue use `0` through `R-1`; after/append use `L+1` with a 1000 ms default duration.
3. **Export Evidence** — atomic export returns the resolved destination and resulting byte count. The GUI renders a prominent `role=status` success panel containing those values.
4. **Disconnect Evidence** — network failure is translated into a Japanese local-server restart/reload instruction and displayed in the same status panel.

## Critic Review

Rejected alternatives:

- Treating a dialog that technically opened somewhere on the desktop as PASS: rejected because a hidden dialog is operationally indistinguishable from a dead button.
- Keeping insertion timing in browser JavaScript: rejected because timing/order is product state and must be deterministic/testable in the backend contract.
- Showing only `SRTを書き出しました`: rejected because it does not prove where the file was written or whether bytes exist.
- Relaxing CSP to address unrelated `fonts.gstatic.com` console noise: rejected because it does not explain the observed control behavior and would weaken the local UI boundary.

## Verification Gate

A release candidate is not handed off until focused tests, **the complete repository pytest suite**, `compileall`, and `git diff --check` pass. Native Windows foreground behavior remains a separate owner-machine acceptance gate.
