# TASK-107 — Settings Modal Reachability Repair

Status: `ACTIVE / ATOMIC_UNIT_A_SOURCE_ACCEPTED / PR_PENDING / PACKAGED_NATIVE_PENDING`

Governance: `DEV-2 STANDARD`

## Authority and responsibility

The Owner reported during TASK-036 packaged-native F0-F10 acceptance on
2026-10-11 that the central AI-model Settings view was clipped and that the
`AIモデル設定を保存` control could not be reached. The Owner also required
coordination with `BVP統括・設計監理` before implementation because another
lane might own the same Shell file.

The coordination read-back established that:

- TASK-106 / PR #608 changes the same `task036_shell_v611.py` file but does not
  change `.modal`, `.settings-layout`, or `.settings-content` CSS;
- PR #608 must be merged first so its accepted Planning recovery work remains
  isolated;
- this defect is a new responsibility and must not rewrite completed TASK-036
  history;
- the repair belongs to new TASK-107 after PR #608.

PR #608 was subsequently merged as current `main`
`79701a2e3f888cf85f22abb7a6d94d385cf4881f`. TASK-107 starts from that exact
identity.

Initial Builder identity:

- base / HEAD / `origin/main`:
  `79701a2e3f888cf85f22abb7a6d94d385cf4881f`;
- branch: `codex/task-107-settings-modal-reachability-20261011`;
- worktree:
  `C:\Users\user\.codex\worktrees\task036-settings-scroll-fix\bai-video-production`;
- initial dirty state: clean.

## Atomic Unit A contract

Goal: make every Settings control, including the central AI-model save button,
reachable at the accepted 1909 x 1074 packaged-native viewport and at shorter
supported viewports without changing model/provider authority.

The implementation must:

1. give the Settings modal a bounded viewport-relative height;
2. preserve a fixed modal header and route remaining height through a
   `minmax(0, 1fr)` content row;
3. remove the Settings layout's fixed minimum-height expansion and constrain it
   to the modal body;
4. provide independent scrolling for the Settings navigation and content pane;
5. preserve keyboard focusability of the Settings tab panel and all existing
   close/Escape behavior;
6. preserve the current central AI-model choices, save handler, public Japanese
   messages and no-Provider/no-billing boundary;
7. preserve TASK-106 Planning recovery and header synchronization unchanged.

## Allowed Files

- `docs/ai-team/tasks/TASK-107/**`
- `src/ai_video_production/task036_shell_v611.py`
- `tests/test_task036_v611_visual_contract.py`

## Prohibited changes and effects

- no AI-model Catalog, route, credential, connection-settings or Provider
  behavior change;
- no Planning application or TASK-106 recovery change;
- no schema, canonical store, queue, Timeline, Resolve or Export change;
- no Product launch, native build, package, installer, model download, paid
  execution, Provider call, Release, Deploy or Production Activation;
- no mutation or cleanup of the running TASK-036 integrated acceptance root;
- no destructive branch/worktree/Evidence cleanup.

## Acceptance

- static visual contract proves the modal owns a bounded height and two-row
  grid with a shrinkable content row;
- Settings layout uses `min-height: 0`, full available height and clipped outer
  overflow so the named inner panes own scrolling;
- Settings navigation and content have explicit shrink/scroll behavior;
- the narrow layout retains a shrinkable content row;
- existing TASK-036 V6.1.1 visual and interaction tests pass;
- diff/scope review shows only Allowed Files;
- packaged-native reachability remains a separate post-integration acceptance
  gate and cannot be claimed from CSS/static tests alone.

## Atomic Unit A source checkpoint — 2026-10-11

Implementation is source-level accepted:

- the Settings modal now owns a bounded `min(760px, 90vh)` height and a fixed
  header plus shrinkable content row;
- the Settings layout and both panes may shrink, while navigation and content
  own their scrolling;
- the narrow layout retains an auto navigation row and shrinkable content row;
- no JavaScript, model-Catalog, Provider, credential, save handler, Planning,
  queue, Timeline, Resolve or Export behavior changed;
- the new visual contract changed from one expected pre-fix failure to PASS;
- V6.1.1 visual/interaction regression: `70 PASS`;
- related desktop/final-review/CLI/Shell regression: `86 PASS`;
- `git diff --check`: `PASS`;
- Critical/High review findings: `0 / 0`.

Canonical source evidence:

- `evidence/source-validation-20261011-r01.md`.

This checkpoint does not close TASK-107. PR integration and a fresh integrated
packaged-native reachability observation remain required before the repair may
be reported as product-level PASS.
