# TASK-036 P-UX-1 — V6.1.1 Mock-to-EXE Visual Convergence Detailed Design

Date: `2026-08-15`
Task: `TASK-036 / P-UX-1`
Profile: `DEV-4`
Status: `LOCAL DESIGN REVIEW PASS / IMPLEMENTATION AUTHORIZED AFTER HOSTED DESIGN CLOSURE`
Canonical mock: `docs/ai-team/product-design/v6-integration/BVP-UI-MOCK-V6.1.1.html`

## 1. Owner Directive and authority

The Owner declares the checked-in V6.1.1 mock to be the best-user-experience
solution and the absolute visual and interaction authority for the packaged
Windows Product. A materially different layout, navigation model or interaction
intent is an acceptance failure even if the underlying feature works.

Authority order for this unit is:

1. current live repository and completed Product contracts;
2. the Owner's absolute V6.1.1 visual-fidelity directive;
3. the canonical V6.1.1 mock for layout and interaction intent;
4. this differential implementation design;
5. historical TASK-036 visual contracts where they do not conflict.

The mock's simulated data, timers and front-end-only success messages are not
Product truth. The runtime must reproduce the design while projecting real
Application Service state and preserving current Authority boundaries.

## 2. Bootstrap / current-main audit

- Implementation Source of Truth: GitHub `main` at
  `0e457e697a8099eac885d7edb88d5e77b0eca431`.
- TASK-026 P-AUDIO-1: PR #86 exact head
  `a907d199a0f70cf05dc24361f512d84cd71163f6`, hosted checks `9 / 9 PASS`,
  merged at exact main `0e457e697a8099eac885d7edb88d5e77b0eca431`.
- TASK-026 remote branch and dedicated checkout: deleted after a clean-tree
  check. The protected Owner checkouts under `D:\BAI` were untouched.
- Active branch:
  `codex/task-036-v611-mock-to-exe-visual-convergence`, created from that exact
  main.
- Stable Product Release remains `v0.21.0`; this visual unit does not select a
  version, Tag or Release.
- Native H3 replay, paid Provider work, Credential mutation, Production Deploy
  and Human ACCEPT/LOCK remain parked.

The audit found a documentation synchronization lag: `PROJECT.md`, Current
State, Task Index and Roadmap still described TASK-026 as hosted-pending after
PR #86 had already merged. This unit corrects that lag without rewriting
TASK-026 history.

## 3. DEV Profile re-decision

`DEV-4` remains required because this change affects the only packaged Desktop
entrypoint, Human Authority presentation, native interaction, accessibility,
all user-facing workspaces and recovery visibility. A visual-only label cannot
reduce the profile: a wrong control binding could start external mutation or
misrepresent a Human decision.

Required gates:

- current-main and source-impact audit;
- exact Allowed Files;
- Builder design and Critic review;
- focused Shell contract tests and full regression;
- embedded JavaScript syntax;
- Windows one-dir EXE build;
- real packaged-EXE interaction, viewport/DPI, keyboard and accessibility
  Evidence;
- hosted CI before main merge.

## 4. Requirement adjudication

| V6.1.1 surface | Current Product truth | Decision for P-UX-1 |
|---|---|---|
| top File/Edit/View/Project/Generate/Export menus | absent; function-first workspace buttons | implement mock hierarchy and concrete command registry |
| H, 1..11, A, Q stage bar | absent | implement as the primary Product navigation |
| Home routes | Planning exists, landing page absent | implement route entry and bind to real workspace state |
| Planning / Scene allocation | TASK-027 Application Service exists | project real snapshot/actions into mock panels; no second store |
| WORLD LOCK | TASK-037/038 Candidate/Audit/LOCK truth exists | project real state; Human decisions stay prepare/apply |
| Scene Design / Start-End | TASK-042 Blueprint v2 is canonical | project exact frame bindings and continuity; no schema fork |
| image/video generation | TASK-040/027/013 services exist | expose Evidence/admission/readiness; no automatic dispatch |
| Audio | TASK-041 plus hosted TASK-026 history exists | project review and Plan persistence; no media execution |
| Asset Review / Assets | TASK-037/038 truth exists | integrate list, audit status and actions |
| Edit | TASK-044 controller exists | reproduce mock's Asset/Viewer/Inspector/Timeline geometry and exact click/seek rules |
| Final Review | Human review foundations exist | show real readiness/blockers; never synthesize approval |
| Export Queue | TASK-044 durable queue exists | reproduce queue page and bind real prepare/cancel/reconcile |
| Quick Generate | TASK-042/040/027 truth exists | implement authority-safe intent/admission UX; no fake result |
| Settings | TASK-028/032/033/034 truth exists | capability/readiness projection; secrets never redisplayed |
| Background Jobs | Shell/generation/export records exist | one persistent job surface; no front-end-only success counter |

## 5. Existing implementation coverage and gaps

The current bridge already exposes bounded methods for Shell state, Planning,
Production Control, Audit, Generation Safety, Continuity, Prompt Evidence,
Generation Queue/execution, generated-output adoption, Audio Workspace,
TASK-026 placement, interactive Timeline, Export Queue, native choosers and the
accepted edit/render/handoff workflow. These methods remain canonical.

The current HTML is materially divergent:

- a 46-pixel function-button header replaces the mock's application chrome and
  38-pixel production stage bar;
- most non-editing capabilities appear as right-side drawers rather than
  integrated workspaces;
- Assets, Viewer, Inspector and Timeline do not use the mock's panel geometry;
- mock Settings, Quick Generate and full-page Export Queue are missing;
- menu hierarchy and concrete commands are missing;
- historical native gates prove launch/function/accessibility but do not prove
  V6.1.1 visual fidelity.

## 6. Design Gap Register

| ID | Severity | Gap | Resolution |
|---|---|---|---|
| UX-01 | Critical | executing the mock demo script would display fictional success | never execute demo state/timers; use Product bridge only |
| UX-02 | Critical | visually correct controls could bypass one-shot Authority | all mutations retain prepare/confirm/apply and revision/hash checks |
| UX-03 | High | no machine-checkable parity definition | add a canonical surface/command contract test derived from the mock |
| UX-04 | High | menus may contain dead clickable commands | bind, navigate, or visibly disable with an exact reason; no silent no-op/toast success |
| UX-05 | High | page changes could lose long-running state | refresh from Application Services and keep job/export identity outside page-local state |
| UX-06 | High | mock example data can be mistaken for Project truth | replace examples with loading/empty/real projections in Product runtime |
| UX-07 | High | current edit click semantics differ by surface | generic Clip selects without seek; ruler/empty lane seeks; Cut Candidate retains review semantics |
| UX-08 | High | responsive layout can clip tab headers | preserve V6.1.1 correction and validate supported viewport/DPI matrix |
| UX-09 | Medium | Browser inspection is currently unavailable due host bootstrap error | no visual PASS from static analysis; packaged native Evidence remains mandatory |
| UX-10 | Medium | mock and runtime may drift later | record the mock path and required surface anchors in tests/docs |

Unresolved Critical/High after the design decisions: `0 / 0`.

## 7. Architecture and source curation

The Product continues to have one Shell, one bridge and one set of Product
stores. P-UX-1 changes the view composition, not Domain ownership.

```text
canonical V6.1.1 visual/interaction contract
                    |
                    v
packaged pywebview / WebView2 Shell
                    |
        allowlisted Task036ShellBridge
                    |
existing TASK-027/037/038/039/040/041/042/044/026 services
                    |
        existing Project children + Manifest
```

The canonical mock remains a design artifact. Its CSS/layout/DOM intent is
ported into a Product-owned runtime template. Its demo JavaScript is not copied
as behavioral authority. The runtime template must carry an explicit
`data-bvp-ui-contract="V6.1.1"` marker.

No new Product schema, migration, store or provider adapter is authorized.
Existing Blueprint v2, Candidate/Audit, Prompt, Queue, Audio and Timeline
identities are reused. Old Project open/save behavior therefore remains
unchanged and rollback is a code-only rollback to the previous Shell template.

## 8. Page-to-service contract

| Page | Read models | Mutating command boundary |
|---|---|---|
| Home | Shell snapshot / recent bound project | navigation and native open chooser only |
| Planning / Scenes | `planning_snapshot` | current planning prepare/apply contracts |
| WORLD LOCK / Asset Review / Assets | `production_snapshot`, `audit_snapshot` | exact Candidate/Audit/LOCK prepare/apply only |
| Scene Design | Planning, Production, Continuity, Prompt | existing versioned prepare/apply operations |
| Start/End / AI Video | Prompt, Queue, Safety, execution status | admission and separately confirmed local execution only when already authorized |
| Audio | Audio Workspace and TASK-026 placement snapshot | existing decision and Plan prepare/apply only |
| Edit | Review + interactive Timeline snapshot | TASK-044 selection/seek/trim commands and Human review contracts |
| Final Review | aggregate read projection | no synthetic ACCEPT; route to owning review action |
| Export | durable Export Queue snapshot | job-level prepare; cancel/reconcile only; execute-all cannot bypass per-job confirmation |
| Quick | Prompt/Provider capability and Queue projection | create bounded intent/admission; no implicit Provider call or Product adoption |
| Settings | current capability/catalog/credential readiness | existing settings ownership only; secret value never returned or rendered |

## 9. Navigation and command registry

Primary navigation must match the mock exactly:

`Home -> Planning -> Scenes -> WORLD LOCK -> Scene Design -> Start/End -> AI
Video -> Audio -> Asset Review -> Edit -> Final Review -> Export`, plus `Assets`
and `Quick Generate` utility destinations.

Top menus must be concrete. Each command entry declares:

- stable command ID;
- destination or bridge method;
- read/navigation/mutation risk;
- required selection/context;
- enabled/disabled reason;
- confirmation and recovery behavior.

No clickable menu item may merely claim success. A not-yet-supported command is
rendered disabled with an accessible reason and cannot call the bridge.

## 10. Interaction contract

- stage/menu/tab selection is keyboard reachable and has visible focus;
- generic Clip click selects only;
- Timeline ruler click/drag, draggable playhead and empty-lane click seek;
- horizontal Timeline scroll and ruler use the same viewport origin;
- Cut Candidate click continues to select the Human review candidate and does
  not inherit generic seek behavior;
- pending confirmation becomes unusable when Project revision or bound hash
  changes;
- page navigation never converts pending, unknown or interrupted work to PASS;
- dialog, menu and drawer focus returns to the invoking control;
- no left/right panel header starts clipped at supported viewport/DPI;
- mock geometry and visual hierarchy are the acceptance baseline, not a loose
  inspiration.

## 11. Error, recovery, idempotency and STALE

- bridge errors appear in one persistent status/toast region with the operation
  identity; they are not swallowed by page navigation;
- recovery-required records remain visible after restart;
- unknown Provider/export state is never automatically retried;
- exact duplicate Product operations retain existing idempotency behavior;
- queued work whose Project/Timeline/Plan binding changes is shown as STALE and
  cannot execute without re-prepare;
- UI-local selection may reset safely; Product decisions never depend only on
  UI-local state.

## 12. Security, cost and Human Authority

- no new egress or Credential read path;
- no paid operation is added or started;
- no Secret value is included in HTML, logs or view models;
- local/free generation remains a separately prepared operation and preserved
  uncertain executions are never replayed;
- Human GO, ACCEPT, LOCK, Cut Plan approval, external NLE mutation and Export
  keep their existing explicit confirmation contracts;
- disabled state is truthful and cannot be changed to enabled by CSS alone.

## 13. Performance and accessibility

- DOM lists must support bounded rendering or virtualization before claiming
  the documented large-list envelope;
- Timeline rendering continues to use the TASK-044 bounded viewport instead of
  producing a DOM node for every frame;
- supported baseline: 1280x720, 1440x900 and 1920x1080 at 100%, 125%, 150% and
  200% effective scaling where the host can safely test it;
- keyboard navigation, focus-visible, Narrator/UI Automation names, status live
  regions, menu Escape behavior and focus restoration are required;
- real multi-monitor movement remains part of native acceptance when available.

## 14. Implementation slices

### P-UX-1A — Shell composition convergence

- canonical application chrome, menus and stage bar;
- integrated page container and all mock destinations;
- mock-converged Edit Assets/Viewer/Inspector/Timeline geometry;
- Settings, Jobs, Quick and Export surfaces;
- real bridge projection for existing capabilities;
- every control bound, navigational or truthfully disabled.

### P-UX-1B — interaction and state convergence

- complete command-registry bindings;
- mock selection/seek/scrub/scroll/focus behavior;
- persistent job/error/recovery presentation;
- large-list/long-Timeline refinements.

### P-UX-1C — packaged native closure

- clean one-dir build;
- screenshot/state comparison against the canonical mock;
- actual clicks, drags, scroll, menus, dialogs, keyboard, DPI and accessibility;
- final Critic and hosted closure.

AUTONOMY may merge safe atomic slices, but no slice may claim overall visual
parity before P-UX-1C Evidence passes.

## 15. Exact Allowed Files

Design/authority unit:

- `PROJECT.md`
- `docs/ai-team/current-state.md`
- `docs/ai-team/task-index.md`
- `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md`
- `docs/ai-team/product-design/v6-integration/BVP-PRODUCT-WORKFLOW-V6-UX-INTERACTION-CONTRACT.md`
- `docs/ai-team/tasks/TASK-036/ui-layout-visual-contract-v1.0.md`
- this document

Implementation unit after hosted design closure and fresh-main reselection:

- `src/ai_video_production/task036_shell_ui.py`
- one optional Product-owned V6.1.1 Shell resource/module below
  `src/ai_video_production/`
- `pyproject.toml` and `packaging/task036_shell.spec` only if the chosen runtime
  resource requires packaging changes
- focused TASK-036 Shell/UI/native tests under `tests/`
- focused TASK-036 native gate helpers under `tools/windows/`
- `CHANGELOG.md` and the Product-owned Current State/Task/Roadmap/Evidence files
  needed for truthful synchronization

Excluded without a new decision:

- Domain schemas and Product stores;
- Provider, paid, Credential or native-generation adapters;
- Resolve/Cubase mutation code;
- package version, Tag, Release and Production Deploy;
- BAI Development OS repository files.

## 16. Regression and native acceptance

Automated:

- canonical mock surface/label/command parity contract;
- no mock demo timer, random progress or synthetic success in runtime HTML;
- bridge allowlist and forbidden-operation assertions;
- existing TASK-036/026/027/037..044 focused regression;
- full Windows and WSL2 pytest;
- compileall, JavaScript syntax and `git diff --check`;
- Windows one-dir EXE build.

Native interaction:

- launch the packaged EXE from a clean owned test Project;
- capture Home, WORLD LOCK, Scene Design, Edit, Quick, Settings and Export;
- open every top menu and verify concrete item enable/disabled reasons;
- verify page navigation and focus restoration;
- verify Clip selection does not seek, ruler/empty lane seek, ruler drag scrubs,
  playhead drag and horizontal scroll synchronization;
- verify no clipped panel/tab header at the supported matrix;
- verify keyboard and UI Automation/Narrator names;
- verify errors/recovery survive navigation and no operation is falsely shown as
  complete.

Static HTML, syntax, unit tests, build success or historical native TASK-036
Evidence are necessary but insufficient for `V6.1.1_VISUAL_PARITY_PASS`.

## 17. Critic review

Critic challenged the design against the mandatory V6 questions:

- New-looking Product lifecycles already exist and are reused; no second store
  is created.
- No migration is needed because this unit changes only the Shell projection.
- Restart truth comes from existing persisted services, not page-local state.
- Project/hash changes keep existing STALE and one-shot rejection behavior.
- Provider timeout/unknown state is visible and never auto-retried.
- paid work and credentials remain gated and secret-free.
- Start/End may use different Space/Composition and multiple Characters through
  existing Blueprint v2 projection.
- Master SRT and audio timing authority remain in their existing owners.
- Quick-generated outputs cannot become adopted Product Assets without the
  existing audit/adoption path.
- Export jobs bind existing Project/Timeline/Plan identities and become STALE
  when those identities change.
- generic Clip and Cut Candidate seek semantics remain distinct.
- 200% DPI/multi-monitor and real interaction require packaged native Evidence.

One Critical finding (fictional mock behavior) and three High findings (dead
commands, Authority bypass risk, and parity claims without native Evidence) were
found and resolved in this design. Final unresolved Critical/High: `0 / 0`.

## 18. Judge / final plan

Decision: `PASS_WITH_SEQUENTIAL_NATIVE_EVIDENCE`.

The design unit is authorized for a documentation-only hosted PR. After all
hosted checks pass, exact main merge and branch/checkout cleanup, AUTONOMY must
fresh-clone main and implement P-UX-1A first. P-UX-1A/B may advance in safe
atomic PRs. Overall visual parity remains unclaimed until P-UX-1C real packaged
EXE Evidence passes.
