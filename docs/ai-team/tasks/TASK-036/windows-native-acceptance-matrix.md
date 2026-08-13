# TASK-036 — Windows Native Acceptance Matrix Ver.0.9

- Date: 2026-08-13
- Status: `DESIGN_AHEAD / EXECUTION_AFTER_R0_AND_TASK036_IMPLEMENTATION_AUTHORIZATION`
- Purpose: prevent a shell from being declared complete based only on browser/headless tests.

## 1. Gate levels

### W0 — Packaging Spike

Proves the selected desktop runtime can be packaged and launched.

### W1 — Shell Native UX

Proves dialogs, focus, DPI, lifecycle and recovery.

### W2 — Minimum Editing E2E

Proves the complete customer-visible editing flow with real Resolve integration.

Only W2 can close TASK-036 as `NATIVE_VALIDATED`.

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
- W2 PASS: `MINIMUM_EDITING_PRODUCT_MVP_PASS`

W0/W1 must not be described as minimum editing Product completion.
