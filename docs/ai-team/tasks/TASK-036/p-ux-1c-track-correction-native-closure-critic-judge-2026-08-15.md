# TASK-036 P-UX-1C Track Correction Native Closure / Critic / Judge

Date: `2026-08-15`
Task unit: `TASK-036 / P-UX-1C`
Lock: `BVP-LOCK-TASK036-PUX1C`
Canonical UX authority: `docs/ai-team/product-design/v6-integration/BVP-UI-MOCK-V6.1.1.html`
Implementation base: `25e2e04fb3360af77017a4a42e868fc95b15ec80`
Fresh main audited: `841cda2e5f4eb4dbc5304d5f57afe49392723825`
Decision: `TRACK_CORRECTION_PASS_FOR_HOSTED_REVIEW_AFTER_FRESH_MAIN_REBASE`

## Closed scope

This unit closes the bounded Track correction and packaged native proof only.
It implements and verifies:

- Video, Subtitle, Audio, SE and BGM category derivation without changing the
  released Timeline serialization;
- add/remove routing through the existing Python prepare/confirm/apply path;
- minimum one remaining Track in every canonical category;
- visibility and lock controls for every projected Track;
- mute and solo controls for audio Tracks;
- Python-owned Track height from `30` through `92`;
- exact-owned packaged process launch/close, isolated pywebview profile,
  display movement and conversation-free restart.

The unit does **not** claim whole-surface `V6.1.1_VISUAL_PARITY_PASS` or overall
TASK-036 completion. Remaining screen gaps are enumerated in
`p-ux-1c-v611-element-parity-audit-2026-08-15.md` and remain open.

## Failure and recovery evidence

1. The first final-gate attempt observed native caption buttons and incorrectly
   treated any non-empty button list as WebView readiness. It then failed before
   Product controls were available. The gate now waits for the exact Home and
   File semantic controls and reports observed names on timeout.
2. The next attempt passed Track discovery/state round trips but failed because
   the Track-height control was absent. The installer used the ID-only `$`
   helper with the CSS selector `.zoomrow`. It now uses
   `document.querySelector('.zoomrow')`; a static regression marker and native
   range-value round trip prevent recurrence.
3. `evidence/native/task036-pux1c-20260815-01` is retained as the pre-final
   baseline. Its JSON predates the final Track controls and must not be used to
   claim this closure.
4. Only `evidence/native/task036-pux1c-20260815-02` is the final native Evidence
   for this correction. It was regenerated from the final clean build after both
   recovery changes.

No unknown process, Owner project, Provider, Credential, Resolve, Cubase,
Human ACCEPT/LOCK, version, Tag, Release or Deploy operation was started.

## Final packaged native Evidence

Evidence:
`evidence/native/task036-pux1c-20260815-02/task036-pux1c-native-closure.json`

- package SHA-256:
  `ee15487e237c630f750512322963eaed5e9632e4e79b4be6442464d2d134ac38`;
- copied complete one-dir package to an owned short path: `PASS`;
- explicit pywebview private mode: `PASS`;
- canonical Track controls present: `PASS`;
- visibility / lock / mute Python round trip: `PASS`;
- Track height Python round trip: `44 -> 52`, `PASS`;
- Timeline zoom, scroll and native pointer scrub: `PASS`;
- native media picker cancel without exit: `PASS`;
- all three display moves and containment checks: `PASS`;
- exact-owned first and second process exit: `PASS`;
- conversation-free private-profile restart: `PASS`;
- mock demo state used: `false`;
- Product projection used: `true`.

The final `05-edit-after-scrub.png` was visually inspected against the canonical
Track region. It contains the five add actions, per-Track visibility/lock/remove,
audio mute/solo and the Track-height range. The in-app browser automation could
not initialize because its local kernel-assets path was unavailable, so no
browser-rendered full-surface PASS is claimed; the canonical HTML structural
audit plus packaged native capture and UI Automation are the evidence used here.

## Verification

- focused Track/native contracts: `34 passed`;
- embedded JavaScript `node --check`: `PASS`;
- Windows `compileall`: `PASS`;
- Windows full regression: `1174 passed, 1 expected non-Windows skip`;
- WSL2 Ubuntu `compileall`: `PASS`;
- WSL2 Ubuntu full regression: `1175 passed`;
- clean Windows one-dir PyInstaller build: `PASS`;
- packaged P-UX-1C native gate: `PASS`;
- `git diff --check`: `PASS`.

The WSL virtual environment was created under an exact temporary path and was
absent after the run. Build output remains under ignored `builds/` and is not a
release artifact.

## Final Critic — pass 1

1. **High — false readiness:** native caption buttons could advance the gate
   before Product HTML was accessible. Corrected with exact semantic readiness.
2. **Critical — missing canonical part:** Track height existed in controller
   code but was not inserted into the rendered DOM. Corrected and proven through
   UI Automation range-value mutation.
3. **High — weak regression marker:** the prior static test only proved that an
   installer function existed. It now proves the correct CSS query path; native
   Evidence proves actual rendering and Python authority.
4. **High — stale Evidence reuse:** the pre-final package does not contain all
   Track closure fields. It is explicitly baseline-only and the final package
   has a different SHA and Evidence directory.

Unresolved Critical/High after correction: `0 / 0`.

## Final Critic — pass 2

1. Category protection is independently tested for Video, Subtitle, Audio, SE
   and BGM, including projection/replay behavior.
2. Presentation state remains Python-owned and snapshots continue to state
   `durable_state_in_javascript=false`.
3. Native cleanup targets exact process objects and exact verified temporary
   roots; no broad process or directory cleanup is used.
4. The changed-file set remains inside `BVP-LOCK-TASK036-PUX1C` Allowed Files
   and does not overlap TASK-046 P-VS-1A.
5. The closure wording is bounded to the Track correction. The element audit's
   remaining page gaps stay open.

Unresolved Critical/High: `0 / 0`.

## Judge

Decision: `PASS_FOR_HOSTED_REVIEW_AFTER_FRESH_MAIN_REBASE`.

Before publication, the branch must be rebased onto exact current `origin/main`,
the changed-file set must remain within the hosted Lock with overlap `0`, and
all hosted checks must pass. Main direct push is prohibited. Exact main merge
and post-merge CI/Security are still required before this Lock can be declared
`HOSTED_CLOSED`.
