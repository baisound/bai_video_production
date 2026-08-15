# TASK-044 — P-NLE-4 Implementation, Native Validation and Critic Evidence

- Date: `2026-08-15`
- Baseline: exact main `c23083e6fa1f8513b14010ece1c2a92c51c47916`
- Branch: `refactor/task-044-p-nle4-shell-ui-native`
- Queue unit: `BVP-TASK-044-P-NLE-4 / IMPLEMENTATION`
- Result: `LOCAL_IMPLEMENTATION_AND_NATIVE_PASS / HOSTED_PENDING`

## Implemented boundary

- the existing TASK-036 Shell now renders Python-owned dynamic semantic tracks,
  a rational viewport and a DOM page bounded to 500 clips;
- generic clip selection, ruler/keyboard seek, Fit Entire/Selection and IN/OUT
  remain distinct reversible session operations;
- trim preparation uses the current Python-owned Project Manifest identity and
  never asks a user to type a checksum or stores durable truth in JavaScript;
- accessibility names expose track role, media kind, exact frame range, state
  and review-Candidate identity without conflating selection and review;
- the trusted launcher lazily derives the NLE from the accepted TASK-036
  projection and binds TASK-044 edit/Export applications only when a current
  Product Project Manifest exists; legacy projects remain readable;
- Export rows expose exact operation identity, state version, safe cancel,
  per-job confirmation and typed UNKNOWN recovery. There is no Execute All
  button and no blanket external authority;
- UNKNOWN success requires exact result identity plus passing Render QA proof.
  MARK_FAILED and REQUIRE_HUMAN do not replay external work;
- the pywebview bridge keeps the rich NLE controller graph private and exports
  only typed allowlisted bridge methods;
- the native minimum window is `760 x 600`, allowing the existing sub-900px
  responsive layout to activate.

No Provider, paid execution, credential mutation, Production Deploy, real
Resolve/Cubase/media mutation, version, Tag or Release operation was performed.

## Critic review

Cycle 1 found three High issues: the `1100px` native minimum prevented the
narrow layout from activating; trim asked the user to type a Manifest checksum;
and Export recovery existed only as presentation. These were closed with the
`760px` minimum, Python-owned Manifest binding and per-job typed cancel/reconcile
methods.

Cycle 2 found pywebview could recursively inspect the publicly stored controller
object and that explicit zoom, bounded track paging and roving clip focus were
not yet complete. The controller/factory are now private Bridge attributes;
focused tests assert that no public controller attribute exists. Typed viewport
updates normalize scale and bound frames/tracks, and the native recheck confirms
zoom, horizontal scroll and roving focus without recursion/API-discovery warning.
Unresolved Critical/High: `0 / 0`.

## Automated validation

- focused P-NLE-4/Export/launcher/Shell: Windows and WSL2 `60 / 60 PASS`;
- full Windows Python 3.12: `1109 passed, 1 skipped` (the skip is the declared
  non-Windows Credential Vault contract);
- full WSL2 Ubuntu using the existing Phase G venv: `1110 / 1110 PASS`;
- compileall: `PASS`;
- `git diff --check`: `PASS`;
- 10,000-clip projection: maximum returned clips `500`, deterministic next
  offset `500`;
- in-app Browser automation adapter: `UNAVAILABLE`; Node kernel startup failed
  with `failed to write kernel assets ... os error 3`. This is recorded as a
  tooling failure, not a browser PASS. Native UI Automation was used instead.

## Windows native acceptance

- current-checkout pywebview/WebView2 preflight: `READY`;
- UI Automation tree after load: `99` elements, `undefined` names `0`;
- dynamic names include VIDEO, AUDIO and TEXT media kinds plus frame ranges;
- Source Video selection and keyboard Right Arrow seek: `Frame 0 -> Frame 1`;
- roving focus: keyboard Right Arrow moved focus from Source Video to Cut
  Candidate; zoom changed Source clip geometry `1561 -> 3121` pixels and right
  scroll changed Cut clip left position `794 -> 409`;
- a ten-track fixture projects eight tracks, then a bounded final page of two;
- actual resize/move: `820 x 720` on `DISPLAY2`, `DISPLAY3` and `DISPLAY1`;
- narrow layout is vertically scrollable; after scrolling, Fit/Selection/IN/OUT
  and dynamic clips are on-screen and keyboard reachable;
- READY/UNKNOWN Export sandbox: one per-job confirmation, one safe-cancel,
  ACCEPT_PROVEN_SUCCESS/MARK_FAILED/REQUIRE_HUMAN actions, and `0` Execute All
  buttons; READY safe cancel changed the row to CANCELLED while UNKNOWN remained
  non-replayed;
- final Windows one-dir build: `PASS`, `14,666,105` bytes, SHA-256
  `BA96D3A5C06BC0CA299A24DDFA9EFA5048A212F345222E321B03013285EBC1A2`;
- final packaged EXE: UI Automation `105` elements, dynamic Timeline, two zoom,
  two horizontal scroll and two track-page controls present, `undefined` names
  `0`, VIDEO/AUDIO and Export entry present, normal close PASS;
- direct monitor-DPI API query stalled and was terminated. The result is not
  claimed as a DPI-value PASS; CSS 1.5/2 dppx contracts, mixed-monitor movement
  and packaged native behavior are the bounded accepted Evidence.

## Closure boundary

P-NLE-4 and TASK-044 can become hosted-closed only after PR checks pass, exact
main merge SHA is verified, and branch/checkout cleanup completes. Release and
old-project/native compatibility closure remain TASK-045 ownership.
