# TASK-036 — Windows Native Acceptance Matrix Ver.1.0

- Date: 2026-08-14
- Status: `W0_PASS / W1_PASS / W2_PACKAGED_NATIVE_E2E_PASS / MINIMUM_EDITING_PRODUCT_MVP_PASS`
- Purpose: prevent a shell from being declared complete based only on browser/headless tests.

## 1. Gate levels

### W0 — Packaging Spike

Proves the selected desktop runtime can be packaged and launched.

### W1 — Shell Native UX

Proves dialogs, focus, DPI, lifecycle and recovery.

### W2 — Minimum Editing E2E

Proves the complete customer-visible editing flow with real Resolve integration.

W2 is necessary but not sufficient to close TASK-036 as `NATIVE_VALIDATED`; the required W0/W1 runtime and native-UX gates must also pass or be formally parked by an explicit release decision.

## 2. Environment inventory recorded for every run

- Windows edition/build;
- display scaling;
- monitor count;
- Python/build tool version;
- packaged Product version/hash;
- selected WebView/GUI backend;
- WebView2 Runtime version if used;
- ffmpeg/ffprobe version;
- DaVinci Resolve version;
- source media fixture identity/hash.

No machine username or unnecessary absolute private paths in portable Evidence.

## 3. W0 — Packaging spike cases

| Case | Expected |
|---|---|
| Packaged EXE launch | one Product window opens; no required terminal |
| clean user profile | application initializes without developer checkout |
| WebView2 present | selected renderer starts successfully |
| WebView2 absent | actionable recovery/bootstrap path, not opaque crash |
| application close | owned UI/server/worker processes terminate safely |
| second launch | defined single/multiple instance behavior; no port collision |
| Unicode install/project path | PASS |
| long path characterization | documented PASS or explicit supported-limit policy |
| dependency inventory | generated and reviewable |

## 4. W1 — Native shell UX cases

### Focus / keyboard

- keyboard reaches navigation and all primary editing actions;
- Tab order is logical;
- Escape/cancel behaves safely;
- focus returns after file/folder dialogs;
- confirmation defaults to non-mutating choice;
- embedded content cannot trap focus permanently.

### DPI / display

- 100%, 125%, 150%, 200% scaling;
- single monitor;
- two monitors with different scaling;
- window moved between monitors;
- native chooser appears on/near active Product window or clearly foregrounds.

### File UX

- open project folder;
- select media;
- open SRT;
- save SRT;
- choose EDITOR_WORK destination;
- cancel each dialog without error state;
- Unicode filenames;
- path conflict/overwrite confirmation where appropriate.

### Lifecycle

- close idle app;
- close while transcription safely cancellable;
- close while external mutation in uncertain state -> recovery warning/fail closed;
- crash/restart after durable backend completion;
- restart reconstructs stage from artifacts/checksums rather than stale UI flag.

### Accessibility smoke

- visible focus;
- status not color-only;
- semantic labels/headings;
- Windows screen reader smoke flow;
- text remains readable at increased scaling.

## 5. W2 — Minimum Editing E2E fixture

Required route:

`Open Project -> Media -> Transcribe -> Subtitle -> Cut Review -> Approve -> Resolve Apply -> Render -> QA -> EDITOR_WORK`

User is prohibited from using terminal, PowerShell, manual browser URL or manual localhost process management during acceptance.

### Required assertions

1. Project opened via native shell.
2. Source media selected via native chooser and bound once.
3. TASK-006 transcription completes and remains bound to the source Asset.
4. Subtitle edits/import/export are available inside Shell.
5. TASK-024 cut candidates are visible with reasons/time ranges.
6. Every candidate reaches explicit CUT/KEEP before approval.
7. TASK-007 plan approval is an explicit human action.
8. Resolve preflight names expected and observed Project.
9. Target is exact Automation-owned `BAI_AUTO_*` Timeline.
10. TASK-010 apply returns `APPLIED` or safe `ALREADY_APPLIED` semantics.
11. TASK-011 real Resolve render completes.
12. TASK-011 QA individual checks are visible.
13. QA policy is not silently weakened on failure.
14. TASK-012 EDITOR_WORK is created only after PASS QA.
15. User can open final folder from the Shell.
16. Restart retains/reconstructs completed state.
17. Human-owned Resolve Timeline is unchanged.
18. Evidence links Plan -> Assembly -> Render QA -> Handoff.

## 6. Negative native cases

- Resolve not running;
- wrong Resolve Project active;
- expected Automation Timeline missing;
- assembly hash conflict;
- render timeout/unknown state;
- render artifact missing/multiple;
- QA duration FAIL;
- QA loudness/true-peak FAIL;
- render modified after QA before handoff;
- destination exists/conflicts;
- stale approved plan after source change;
- app restart after external operation but before UI received completion.

Every case must provide a safe recovery route and must not mutate a human-owned target as a fallback.

## 7. Toolkit fallback trigger

Reopen `ADR-036-001` and evaluate PySide6 as primary if the pywebview/WebView2 candidate cannot satisfy any critical W0/W1 item without disproportionate workaround complexity, especially:

- reliable foreground/native dialog ownership;
- keyboard/focus;
- accessibility;
- stable packaged startup;
- WebView2 runtime recovery;
- worker/server lifecycle;
- security of bridge isolation.

Do not keep a toolkit merely because implementation work has already been spent on it.

## 8. Completion labels

- W0 PASS: `DESKTOP_RUNTIME_SPIKE_PASS`
- W1 PASS: `DESKTOP_SHELL_NATIVE_UX_PASS`
- W2 route PASS: `W2_PACKAGED_NATIVE_E2E_PASS`
- W0 + W1 + W2 closure PASS: `MINIMUM_EDITING_PRODUCT_MVP_PASS`

W0/W1 must not be described as minimum editing Product completion.

## 9. Phase G execution checkpoint — 2026-08-13

R0 backend native gates are closed for TASK-010/011/012. TASK-036 real Windows execution now proves packaged WebView2 launch, HTML-reachable native chooser controls, focus return, multi-instance characterization, Unicode install-path launch and owned-process cleanup.

W0 remains partial because clean-profile and missing-WebView2 recovery are untested and path length 245 fails at an internal packaged DLL path. W1 remains partial because the complete DPI/mixed-monitor/accessibility matrix is unfinished.

W2 passed on 2026-08-14. The trusted packaged launcher completed native media ingest, cached/network-free local FasterWhisper, Subtitle, explicit Human plan approval, exact sandbox Resolve apply, TASK-011 native Render QA and atomic TASK-012 EDITOR_WORK in one session. The final Shell action was `NONE`. Conversation-free restart and Pilot Context Cost remain Phase G closure Evidence and do not broaden the accepted W0/W1 scope.

## 10. Formal W0/W1 parking — 2026-08-14

Clean-profile startup, missing-WebView2 recovery, long-path mitigation, the full DPI/mixed-monitor matrix and Windows screen-reader smoke are `PARKED_TO_PHASE_H2`. They remain unpassed. The release-support boundary is installed WebView2, a normal local install path and the tested single-monitor viewports. W2 remains accepted independently; overall TASK-036 completion remains unclaimed.

## 11. Phase H2 W0/W1 closure — 2026-08-14

The parked remainder was resumed and closed on the v0.20.1 candidate. Clean-profile packaged launch, isolated missing-WebView2 native recovery, an enforced proven 166-character executable-path policy, real three-monitor movement, Windows Narrator/UI Automation semantics and the increased-scale responsive layout contract pass. W0 is `DESKTOP_RUNTIME_SPIKE_PASS`; W1 is `DESKTOP_SHELL_NATIVE_UX_PASS`; W2 remains `W2_PACKAGED_NATIVE_E2E_PASS`. The combined gate is `MINIMUM_EDITING_PRODUCT_MVP_PASS`.
