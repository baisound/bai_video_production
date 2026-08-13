# TASK-036 — H2 W0/W1 Design, Review and Authorization

- Date: `2026-08-14`
- Starting implementation Source of Truth: `main` at `a09f9d2f896d6a967c3c1ec6608d6c7c810b3914`
- Working branch: `codex/task-036-h2-native-closure`
- Governance route: `OWNER_DIRECTED_IMPLEMENTATION`
- DEV Profile: `DEV-4`
- Decision: `IMPLEMENTATION_AUTHORIZED`

## Current OS audit and Registry check

The current checkout was newer than the Phase G handoff package and remained the implementation Source of Truth. `PROJECT.md`, `docs/ai-team/current-state.md`, `docs/ai-team/task-index.md`, the canonical roadmap and the TASK-036 acceptance/parking records agreed that W2 and v0.20.0 were complete while five W0/W1 cases remained parked. Existing untracked raw `evidence/` directories were preserved.

The exact H2 remainder was:

1. clean-profile packaged startup;
2. missing-WebView2 recovery;
3. explicit long-install-path policy;
4. multi-monitor and increased-scale layout coverage;
5. Windows screen-reader smoke.

## Allowed Files

- `src/ai_video_production/task036_native_probe.py`
- `src/ai_video_production/task036_packaged_entry.py`
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/task036_trusted_launcher.py`
- `packaging/task036_windows_entry.py`
- focused TASK-036 tests under `tests/`
- TASK-036 Windows gate scripts under `tools/windows/`
- release metadata and TASK-036 canonical Product documents

No Resolve/Cubase project mutation, paid provider call, Production write, force push or direct main push is authorized by this unit.

## Builder Design

- Make packaged startup run a read-only environment preflight before creating the Shell.
- Require Windows, bundled pywebview, an installed/fixed WebView2 Runtime and a supported executable path.
- If WebView2 is absent, show a native actionable recovery dialog because the frozen executable has no console.
- Enforce an executable-path maximum of 166 characters, the longest previously proven successful packaged launch boundary. The previously failed 245-character path remains outside support.
- Force the accepted `edgechromium` renderer rather than allowing implicit backend selection.
- Add visible focus, skip navigation, semantic labels and a responsive narrow/high-scale layout.
- Add repeatable Windows gates that copy the package outside the checkout, create a disposable empty profile, move the native window across every connected monitor, inspect the Windows Automation tree, run a bounded Narrator session and isolate the missing-WebView2 condition without uninstalling the host runtime.

## Critic Review

One bounded Critic review was performed; no repeated review loop is required.

- Critical/High findings: `0 / 0` after correction.
- Corrected finding: a console-only failure would be opaque for the frozen `console=False` executable. Resolution: native MessageBox presentation with stable error code and recovery action.
- Corrected finding: pywebview previously selected its installed backend implicitly. Resolution: both launch paths now request `edgechromium` explicitly.
- Corrected finding: the former long-path result was only descriptive. Resolution: startup now enforces the evidenced limit before WebView initialization.
- Corrected finding: UI Automation was queried before the WebView document finished loading. Resolution: the native gate waits up to 20 seconds for the semantic tree.
- Residual compatibility risk: the connected monitors are all 100% DPI, so physically changing the Owner's active display settings was rejected. The Product instead has an explicit 125–200%-equivalent responsive layout contract, while actual three-monitor movement, window bounds and Automation semantics are tested natively. Future hardware diversity remains compatibility monitoring, not a TASK-036 functional blocker.

## Final Plan

1. implement the startup/accessibility/display corrections;
2. build a fresh one-dir Windows package;
3. run clean-profile, three-monitor, Narrator and isolated missing-WebView2 gates;
4. run focused and full regression;
5. record closure and exact `0.20.1 / v0.20.1 / stable` patch-release decision;
6. PR, all-green merge, exact main SHA verification, annotated tag, GitHub Release and branch cleanup.

The Owner's instruction to finish TASK-036 authorizes this plan. It does not authorize broadening external-write or paid-execution authority.
