# TASK-036 P-UX-1C Current-main Audit, Builder Design and Authorization

Date: `2026-08-15`
Task: `TASK-036 / P-UX-1C`
DEV Profile: `DEV-4 FOUNDATION CRITICAL`
Status: `IMPLEMENTATION_AUTHORIZED`
Exact base main: `25e2e04fb3360af77017a4a42e868fc95b15ec80`
Branch: `codex/task-036-v611-packaged-native-closure`

## Owner directive and authority

The checked-in `BVP-UI-MOCK-V6.1.1.html` remains the absolute visual and
interaction-intent authority. A materially different packaged EXE is an
acceptance failure. Mock demo records, timers and front-end-only success remain
non-authoritative and must not be introduced into the Product runtime.

The Owner-supplied Voice Studio handoff was reconciled and hosted through PR
#90 before this unit. PR #90 merged at exact main
`25e2e04fb3360af77017a4a42e868fc95b15ec80`; post-merge Security and CI passed,
the remote branch and clean dedicated checkout were removed, and the source ZIP
was retained. Voice Shell implementation remains after P-UX-1C and a successor
canonical mock.

## Current-main audit

- checkout: fresh single-branch clone of exact GitHub `main`;
- worktree at selection: clean;
- open PRs at Voice intake selection: none before PR #90;
- stable release: `v0.21.0`; no version, Tag or Release is selected here;
- P-UX-1A and P-UX-1B runtime changes are already on main;
- focused V6.1.1/Shell/NLE/package baseline: `54 / 54 PASS`;
- clean Windows one-dir build: PASS;
- baseline packaged EXE SHA-256:
  `6f057772b2ed51bf3b953a1c86f97371e6891b09181edb445e1c56301d2edb7b`;
- clean-profile native launch, three-display movement, UI Automation discovery,
  screenshot capture and owned process exit: PASS.

The build checkout path is longer than the already enforced supported
installation limit. Direct launch therefore correctly fails with
`ERR_TASK036_INSTALL_PATH_TOO_LONG`; native acceptance copies the package to an
owned short temporary path and does not weaken that policy.

## Visual differential audit

The initial 1500 x 850 packaged capture switched to the narrow responsive
layout while a 100% headless mock capture retained three columns. This was not
accepted as a Product discrepancy without measuring the environment.

The host has Windows `TextScaleFactor=130`. The existing H2 helper records
monitor DPI as 96 / 100% but does not record the independent text scale. When
the canonical mock is rendered under the equivalent 130% condition, its
application chrome, stage navigation, three-route Home composition, recent /
direct panels, spacing and hierarchy converge with the maximized packaged EXE.
Runtime differences are Product truth only: the current Project replaces mock
sample projects, and capability state replaces the illustrative provider.

Remaining closure gap: the repository has no single reproducible gate that
records actual text scale, menu/keyboard/focus restoration, Settings, Edit
Timeline drag/scroll, native picker cancellation, multi-display movement and
conversation-free restart together. Historical gates cover subsets but are
insufficient for a final P-UX-1C claim.

Owner-directed element-by-element re-audit then confirmed a second, blocking
class of gap. The mock and workflow specification require dynamic Video,
Subtitle, Audio, SE and BGM tracks, category-minimum add/remove, visibility,
lock, mute/solo where relevant and height. The runtime rendered only names and
lanes. The whole-surface inventory also identifies functional-part omissions on
Planning, Scenes, Locks, Scene Design, generation, Audio, review, Assets, Quick
and parts of Edit. See
`p-ux-1c-v611-element-parity-audit-2026-08-15.md`. These are implementation
defects unless an explicit UX-improvement decision replaces a canonical part.

## DEV Profile re-decision

`DEV-4` remains required. The gate exercises the packaged Desktop entrypoint,
native window focus, accessibility projection, Project-bound controllers and
dialog behavior. It must prove that tests do not invoke Provider, paid,
Resolve/Cubase, Human ACCEPT/LOCK, Release or Deploy authority.

## Allowed Files

- `tools/windows/run-task036-pux1c-native-closure.ps1`;
- one focused contract test under `tests/` for the new gate;
- `docs/ai-team/tasks/TASK-036/` P-UX-1C design and Evidence;
- `PROJECT.md`;
- `docs/ai-team/current-state.md`;
- `docs/ai-team/task-index.md`;
- `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md`;
- `CHANGELOG.md`.

The Owner-directed Track defect expands the corrective Allowed Files to:

- `src/ai_video_production/interactive_timeline.py`;
- `src/ai_video_production/interactive_timeline_edit.py`;
- `src/ai_video_production/interactive_timeline_application.py`;
- `src/ai_video_production/task044_nle_shell.py`;
- focused TASK-044/TASK-036 tests required to prove category protection,
  Python-owned state and V6.1.1 UI wiring.

The following become allowed only if the native differential gate finds a real
runtime defect:

- `src/ai_video_production/task036_shell_ui.py`;
- `src/ai_video_production/task036_shell_v611.py`;
- `packaging/task036_shell.spec`.

Excluded without a new decision: serialized Domain schema/store format changes, Provider/Credential
adapters, native generation, Resolve/Cubase mutation, package version, Tag,
Release, Deploy and the BAI Development OS repository.

## Builder design

1. Add one fail-fast PowerShell native closure gate.
2. Resolve and copy the complete one-dir package to a unique owned short path.
3. Create an isolated Windows profile and start the packaged EXE twice.
4. On the first launch:
   - prove semantic application/stage/menu buttons;
   - record monitor DPI and Windows text scale separately;
   - capture Home, File menu, Settings, Export and Edit states;
   - verify Escape closes menu/dialog and restores focus;
   - verify Timeline zoom and horizontal scroll change real geometry;
   - drag the ruler/playhead through native pointer input and require a changed
     controller-derived accessible frame;
   - open and cancel the native media picker without exiting;
   - move the window across all available displays;
   - close only the owned process.
5. On the second launch, require the same semantic controls and normal owned
   exit without any conversation or manual repair.
6. Emit path-free JSON Evidence plus screenshots in an explicitly supplied
   Evidence directory. Temporary profiles/packages are always removed.
7. Add a static contract test that rejects missing safety flags, cleanup,
   text-scale truth or required interaction checks.
8. Run focused tests, Windows and WSL2 full regression, compileall, embedded
   JavaScript syntax, clean build, native gate and `git diff --check`.
9. Correct confirmed Track parity defects without changing released Timeline
   serialization: derive categories, enforce last-in-category protection, add
   Python-owned visibility/lock/mute/solo/height projection, and bind five add
   controls plus per-track controls to the existing durable edit Application.
10. Synchronize current state and roadmap without rewriting historical TASK-036
   release claims.

No Product runtime change is planned unless the gate demonstrates a concrete
defect. An Evidence-only closure is valid because P-UX-1A/B already changed the
runtime and P-UX-1C owns native proof, not feature invention.

The element audit demonstrated a concrete Product runtime defect, so the
conditional runtime boundary is now active. Evidence-only whole-surface closure
is no longer valid.

## Critic review — pass 1

Findings:

1. **High — false scaling claim:** monitor DPI 96 does not prove Windows text
   scale 100. Resolution: record `TextScaleFactor` independently and describe
   the exact native condition.
2. **High — screenshot-only acceptance:** visual similarity cannot prove
   interaction or controller authority. Resolution: UI Automation plus native
   pointer/keyboard operations and before/after accessible state are required.
3. **High — hidden mock state risk:** writing the mock HTML into the EXE would
   reintroduce simulated success. Resolution: the gate inspects the existing
   Product runtime only; no mock JavaScript is copied.
4. **High — broad process cleanup risk:** generic process termination could
   affect Owner applications. Resolution: retain exact `Process` objects and
   close only owned instances.
5. **Medium — long checkout path:** direct build-path launch hits the supported
   fail-closed policy. Resolution: copy to a unique short owned temp path, then
   delete only that verified path.

Unresolved Critical/High after correction: `0 / 0`.

## Critic review — pass 2, element parity

1. **Critical / confirmed:** Track controls present in both mock and written
   specification were absent from the runtime. Resolution: implement the
   controller, bridge and UI correction in this bounded slice.
2. **High / compatibility:** adding state fields to released Track
   serialization would change Timeline checksums and could stale existing
   history. Resolution: category derivation and Python-owned presentation state
   preserve the released serialized shape.
3. **High / deletion safety:** the old `minimum_required` flag alone does not
   prove one track remains in every category. Resolution: preparation and replay
   independently count the effective category and fail closed at one.
4. **High / fake UI risk:** adding mock buttons with JavaScript-only mutation
   would repeat the defect. Resolution: durable add/remove uses existing
   prepare/confirm/apply; presentation state is Python-owned and snapshot-driven.
5. **High / overclaim:** other pages contain confirmed missing functional parts.
   Resolution: this slice may claim Track correction only; whole-surface parity
   remains open and is queued screen by screen.

Unresolved Critical/High for the Track slice after correction: `0 / 0`.
Unresolved whole-surface parity gaps: `OPEN`, explicitly enumerated in the
element parity audit.

## Judge / final plan

Decision: `PASS_FOR_P_UX_1C_IMPLEMENTATION`.

The bounded native-gate/test/Evidence and Track corrective unit is authorized.
Overall `V6.1.1_VISUAL_PARITY_PASS` remains unclaimed until all enumerated
screen corrections, clean packaged gates, full regression, final Critic and
hosted checks pass. Voice Studio runtime,
model download, voice processing, paid/Cloud operations, Human decisions,
external application mutation, versioning and release operations remain
unauthorized in this unit.
