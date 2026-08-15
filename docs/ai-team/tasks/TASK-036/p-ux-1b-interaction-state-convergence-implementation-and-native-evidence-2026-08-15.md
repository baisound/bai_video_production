# TASK-036 P-UX-1B Interaction and State Convergence Evidence

Date: 2026-08-15
Task: `TASK-036 / P-UX-1B`
DEV Profile: `DEV-4 FOUNDATION CRITICAL`
Exact base main: `35b91f29b39372ce38616d1d757b6ef43d68232b`
Branch: `codex/task-036-v611-interaction-state-convergence`

## Decision

The checked-in `BVP-UI-MOCK-V6.1.1.html` remains the absolute visual and
interaction-intent authority. P-UX-1B connects a bounded core interaction unit
to the existing Product bridge and controllers. It does not create JavaScript
durable truth, mock records, random progress, synthetic success, Provider
authority or a second Timeline/Settings/Queue store.

P-UX-1B core is `LOCAL_PASS`. Overall `V6.1.1_VISUAL_PARITY_PASS` remains
unclaimed. P-UX-1C still owns the complete supported viewport/DPI, menu,
keyboard, focus, accessibility and conversation-free packaged restart matrix.

## Implemented interaction convergence

- explicit command registry for Fit Entire, Fit Selection, Set IN, Set OUT and
  Background Jobs instead of scattered command conditionals;
- top-menu open/close, roving keyboard navigation and focus restoration;
- Settings and Background Jobs close/Escape behavior returns focus to the
  actual invoker without stale-button focus jumps;
- all nine canonical Settings categories are operable tabs with category-
  specific read-only summaries and exact existing TASK-028/032/033/034
  authority boundaries;
- Settings never redisplays credentials and does not authorize Provider or
  paid execution;
- Timeline ruler/playhead pointer drag and one-frame keyboard seek use the
  existing `interactive_timeline_seek` controller operation;
- seek requests are serialized/coalesced and the returned Product snapshot is
  authoritative; the front end retains no durable Timeline state;
- Background Jobs refreshes both the real generation and export queue
  projections and never automatically replays work;
- Undo/Redo and Playback remain visibly disabled because the current Shell
  bridge does not yet project their exact availability/controller state.

## Native packaged acceptance

The Windows one-dir build completed with `build-windows-exe.bat`. The owned
build was copied to the dedicated short test path `C:\bvp-pux1b-native` and
launched successfully. Native inspection exercised:

- Settings open, Audio category selection and its exact no-execution boundary;
- File menu display with truthfully disabled unavailable commands;
- Edit Timeline ruler drag from the initial frame to `00:00:06:09`, with the
  red playhead and controller-derived Viewer timecode moving together.

The menu keyboard/focus bindings are covered by the interaction contract, but
the screenshot alone does not prove the complete native focus matrix. That
claim remains assigned to P-UX-1C.

Local capture hashes:

| Capture | SHA-256 |
|---|---|
| `p-ux-1b-settings-audio.png` | `9841695e951d02b430eece25936af95c88de566774dec84c4366c4911a42026a` |
| `p-ux-1b-menu-keyboard.png` | `0103f819c9bad87ea8dc2f6779d48e12f04ae7acf1c4457fbcd70d5affa974d4` |
| `p-ux-1b-timeline-scrub.png` | `4324b42ab020ebbf1851f9fae32d6f077250abc554f4debf152a47eca6e68058` |
| final packaged EXE | `695cc24ab90c12d2e2d29b96290402056f94a5cf6d83b9ec87143e0fc2ac910b` |

The in-app browser kernel remained unavailable, so browser-tool visual
acceptance is not claimed. Native packaged EXE inspection is the bounded
P-UX-1B evidence route.

## Validation

- focused TASK-036/TASK-044/V6.1.1 interaction tests: `50 / 50 PASS` on
  Windows and Ubuntu WSL2;
- Ubuntu WSL2 full regression: `1167 / 1167 PASS`;
- Windows full regression: `1166 passed, 1 intentional non-Windows skip`;
- embedded JavaScript `node --check`: PASS;
- Windows one-dir EXE build: PASS;
- `git diff --check`: PASS.

## Critic review

The implementation review found two focus defects: opening Background Jobs
through the command registry restored focus to the menu too early, and Escape
with no active overlay/menu could jump to a stale invoker. Both were corrected
and the focused contract was rerun. Static contract drift around clip keyboard
selection and Settings tab bindings was also corrected without weakening the
contract. Unresolved Critical/High findings: `0 / 0`.

## Boundary and next action

Hosted PR checks, exact main merge and branch/checkout cleanup remain before
P-UX-1B hosted closure. After that closure, the Owner-supplied Voice Studio
Local AI handoff must be read from its `README-FIRST.md` order and reconciled
against the new exact main before P-UX-1C or another Product unit is selected.

Native H3 replay, paid Provider execution, Credentials, Human ACCEPT/LOCK,
Resolve/Cubase mutation, Production Deploy, version change, Tag and Release
were not performed.
