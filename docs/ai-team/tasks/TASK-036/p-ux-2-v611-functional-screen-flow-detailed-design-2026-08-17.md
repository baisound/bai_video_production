# TASK-036 P-UX-2 — V6.1.1 Mock-Absolute Functional Screen Flow

Date: `2026-08-17`
Task: `TASK-036 / P-UX-2`
Profile: `DEV-4`
Status: `DESIGN_REGISTERED / IMPLEMENTATION_QUEUED / FUNCTIONAL_FLOW_NOT_COMPLETE`
Canonical visual authority: `docs/ai-team/product-design/v6-integration/BVP-UI-MOCK-V6.1.1.html`
Implementation audit base: `a943c2a9c0f2a7e9c812379146f2e77b2e9746d8`

## 1. Owner directive

The checked-in V6.1.1 HTML mock is the absolute visual and interaction-layout
authority. Product screens must not replace its page order, hierarchy, panel
geometry, labels or interaction intent with a different design merely because
backend services already exist.

Visual presence is not functional completion. A screen is complete only when
its visible content is projected from canonical Product truth, its enabled
controls call the owning typed Application Service, the resulting state is
read back into that same screen, and the next screen receives the exact output
identity. The end-to-end acceptance route is:

```text
Home / Project / Media
  -> Planning
  -> Scenes
  -> WORLD LOCK
  -> Scene Design
  -> Start/End + AI Video + Audio
  -> Asset Review / Assets
  -> Edit
  -> Final Review
  -> Export Queue
  -> Render QA / output read-back
```

The mock's sample records, random progress, timers and toast-only success remain
non-authoritative. They must be replaced by real state or by a truthful,
accessible disabled reason until the owning service exists.

## 2. Fresh implementation audit

The current runtime preserves the mock's outer composition but does not close
the full production flow:

- mock and runtime both expose all `14 / 14` primary pages;
- runtime navigation contains all `14 / 14` primary destinations;
- the mock contains `253` buttons while the runtime contains `126`;
- the runtime contains `37` disabled buttons and `36` explicit disabled
  reasons;
- P-UX-1C proves `V6.1.1_VISUAL_PARITY_PASS`, native navigation, focus,
  accessibility and truthful disabled presentation;
- P-UX-1C does not prove that every mock workflow is connected to Product
  state or that a user can travel from media intake to a verified export.

Material blockers found in the runtime template include:

- Proposal generation is not connected;
- Scene revision create/update/delete and Timeline Contract finalization are
  not connected;
- Player transport controls are not connected;
- Asset insertion/replacement and tag truth are incomplete;
- typed Final Approval is not connected;
- Export preset selection and queue insertion are not connected;
- Resolve/Premiere handoff remains separately gated;
- several pages show projections but cannot yet perform the mock-intended next
  operation.

Therefore the current state is:

`VISUAL_PARITY_PASS / FUNCTIONAL_SCREEN_FLOW_NOT_COMPLETE`.

## 3. Authority order

1. Owner directive in this design;
2. canonical V6.1.1 HTML mock for visible layout, page order and interaction
   intent;
3. canonical Product domain/Application Service truth for data and effects;
4. this end-to-end flow contract;
5. historical TASK-036 designs where they do not conflict.

The visual mock cannot create fake Product truth. Backend convenience cannot
silently change the mock. Where the two need reconciliation, preserve the mock
surface and route it through an explicit typed adapter with truthful
loading/empty/blocked/error states.

## 4. Definition of a functionally connected screen

Each screen must publish one machine-checkable contract row containing:

- stable page and control IDs from the mock;
- canonical source service and snapshot/revision/hash;
- loading, empty, ready, blocked, error, stale and recovery-required states;
- enabled condition and exact disabled reason;
- typed command and prepare/confirm/apply boundary;
- effect classification and required Human authority;
- success, failure and unknown read-back rules;
- output identity handed to the next screen;
- restart/reopen behavior;
- focused, cross-screen and packaged-native Evidence.

A button click, toast, local JavaScript mutation, HTTP `200`, ACK or queue
reservation is not success. Success requires the owning service's canonical
receipt and a fresh projection that shows the resulting state.

## 5. End-to-end screen flow contract

| Gate | Mock surface | Canonical input | Required connected operation | Output / next-screen binding | Current state |
|---|---|---|---|---|---|
| F0 | Home / File | Project Manifest, Asset Registry | open/create supported Project, media ingest, checksum/rights/readiness | exact Project + source Asset IDs -> Planning | `PARTIAL` |
| F1 | Planning | Creation Intent, Proposal, cost/rights | create/revise Proposal and explicit Human GO through existing ownership | Approved Plan hash -> Scenes | `PARTIAL`; generation entry missing |
| F2 | Scenes | Approved Plan, Blueprint v2, Scene Boundary | list/create/revise/remove Scenes and finalize exact frame coverage | Scene/Blueprint revision -> WORLD LOCK | `PARTIAL`; revision operations missing |
| F3 | WORLD LOCK | Slot/Candidate/Audit/Continuity truth | inspect, audit, Human ACCEPT/LOCK, invalidate stale bindings | exact LOCK set + snapshot -> Scene Design | `CONNECTED_BOUNDED` |
| F4 | Scene Design | Blueprint, LOCK, Prompt Registry, continuity | edit scene intent/prompt/reference bindings without forking truth | compiled scene revision -> generation pages | `PARTIAL` |
| F5 | Start/End, AI Video, Audio | compiled prompt, rights, capability, Resource, Voice/Audio plans | prepare/admit/confirm each generation or audio operation; reconcile UNKNOWN | generated Candidate/Evidence IDs -> Asset Review | `PARTIAL`; execution remains gated by provider/license/consent |
| F6 | Asset Review / Assets | Candidate/Audit/Asset Registry | Human adopt/hold/reject, publish verified derived Asset, insert/replace proposal | adopted Asset + exact target binding -> Edit | `PARTIAL`; insertion/replacement incomplete |
| F7 | Edit | Timeline, subtitle, audio placement, Asset truth | playback/seek, select, trim/move, undo/redo, insert/replace, save/reopen | immutable Edit/Timeline revision -> Final Review | `PARTIAL`; playback and several mutations missing |
| F8 | Final Review | Edit, QA, Privacy, rights, stale/recovery state | aggregate blockers and create typed Human final approval | approved render intent -> Export | `BLOCKED`; typed final approval missing |
| F9 | Export | approved render intent, preset, destination, capability | create one durable Job, individually confirm dispatch, cancel/reconcile | Render artifact + QA/Evidence receipt | `PARTIAL`; preset/queue-add missing |
| F10 | Output | Render QA and published artifact | checksum/media/duration/loudness/read-back and safe handoff | verified output or explicit failure/UNKNOWN | backend exists; unified UI closure missing |

`CONNECTED_BOUNDED` means the screen has a usable bounded path, not that all
future features on that page are complete.

## 6. Implementation roadmap

### P-UX-2A — machine-checkable flow inventory

- derive the canonical page/control inventory from the V6.1.1 mock;
- record every runtime control as `BOUND`, `NAVIGATION`, `DISABLED_WITH_REASON`
  or `MISSING`;
- add a page-to-service registry and cross-screen identity contract;
- fail tests when mock controls disappear, become toast-only, or lose their
  canonical source/output binding.

Exit: every visible primary action has an owner, state contract and next-screen
identity. This slice changes no external application or media.

### P-UX-2B — intake, planning and scene contract

- close F0 through F2 without creating a second Project, Asset, Proposal,
  Blueprint or Scene store;
- connect Project/media intake progress and failures back to Home;
- connect Proposal creation/revision and Scene revision/finalization through
  typed prepare/confirm/apply services;
- make reopening reproduce the same Project/Plan/Scene identities.

Exit: an ingested video can reach a finalized Scene/Blueprint contract through
the mock-absolute screens.

### P-UX-2C — generation, audio and asset adoption

- close F3 through F6 using TASK-013/014/016/020/026/037..041/046..048 truth;
- keep provider download, license acceptance, paid work, Consent and native
  execution as explicit gates;
- replace progress animation with durable Job/Evidence state;
- ensure Candidate adoption produces a verified Asset before Edit can use it.

Exit: all required scene/audio inputs are either adopted Assets or explicit
blockers; no mock Candidate becomes Product truth by UI state alone.

### P-UX-2D — edit, final review and export

- close F7 through F10 using TASK-010/011/016/021/022/026/043/044 truth;
- connect transport, selection, timeline mutations, undo/redo and replace;
- add a typed aggregate Final Review service without stealing underlying Human
  authorities;
- connect preset/destination validation, durable queue creation, individual
  dispatch confirmation, render QA and output read-back;
- preserve `UNKNOWN` without automatic retry or false success.

Exit: the supported fixture travels from an approved Timeline to a verified
output artifact in one packaged application flow.

### P-UX-2E — packaged native vertical closure

- clean-profile packaged Windows execution;
- restart at every F0..F10 boundary and recover canonical state;
- mock-reference screenshots at supported viewport/DPI values;
- keyboard, Narrator/UI Automation, focus and error persistence;
- one synthetic/offline fixture and one Owner-authorized real-media fixture;
- exact exported file bytes/hash/media properties and QA receipt read-back.

Exit: `MOCK_ABSOLUTE_FUNCTIONAL_EXPORT_FLOW_PASS`.

## 7. Scheduling and dependencies

P-UX-2 is the Product-integration priority after the two currently active
atomic units reach a safe terminal. It must run before any roadmap milestone
claims the complete V6 application or Production Pilot UI.

```text
P-UX-2A
   |
   v
P-UX-2B -----------+
   |                |
   v                |
P-UX-2C             |
   |                |
   +-------> P-UX-2D
                  |
                  v
               P-UX-2E
```

- P-UX-2A is immediately runnable and effect-free.
- P-UX-2B may start after the registry contract is fixed.
- P-UX-2C may develop provider-neutral adapters while effect gates remain
  parked.
- P-UX-2D may implement offline/synthetic flow while external Resolve/render
  execution remains separately authorized.
- P-UX-2E requires all preceding receipts and the applicable real-media/native
  authorities.

## 8. Ownership and non-duplication

TASK-036 owns only unified presentation, bridge composition and cross-screen
flow. Existing owners remain unchanged:

- Project/durable/recovery: TASK-043;
- Asset/rights/checksum: TASK-003/037;
- Scene boundary and frame mapping: TASK-005/022;
- Planning/orchestration: TASK-027/042;
- Candidate/Audit/LOCK: TASK-037/038;
- generation/prompt/queue: TASK-013/040/027;
- narration/voice: TASK-014/046..048;
- privacy/resource: TASK-016/020;
- audio placement/workspace/finishing: TASK-026/041/035;
- Timeline/Export queue: TASK-044;
- Resolve/render QA/handoff: TASK-010/011/012.

P-UX-2 adapters must call these owners; they must not copy their schemas,
stores, state machines or authority decisions.

## 9. Safety and Human gates

The Owner's standing download/install/application-operation authority does not
convert the following into automatic Product actions:

- license or rights acceptance;
- paid provider or credential use;
- voice/recording Consent, Dataset adoption or training;
- Privacy approval, external notification or publication;
- destructive retention/delete/legal-hold decisions;
- Resolve/REAPER/native mutation without a bound Project operation;
- Release, Deploy or Production Activation.

The flow must show these as explicit blockers and allow unrelated screens to
remain usable.

## 10. Verification matrix

Each slice requires:

- mock/runtime page and control inventory parity;
- bridge allowlist and source/output identity tests;
- focused page tests plus adjacent-page handoff tests;
- stale, tamper, duplicate, timeout, UNKNOWN, cancel and restart tests;
- no random progress, sample Product record or toast-only success;
- Windows and WSL2 full regression;
- embedded JavaScript and Python syntax;
- packaged Windows interaction for changed surfaces;
- Critic reviews for Builder, Security/Authority and Operations/UX;
- hosted checks and post-merge CI/Security.

Final vertical acceptance must prove:

1. media selected and ingested;
2. Project/Plan/Scene identities survive restart;
3. required Asset and Human gates are visible and enforced;
4. Timeline edits are persisted and reopen identically;
5. Final Review cannot approve stale or blocked state;
6. exactly one Export Job is created and individually confirmed;
7. the output artifact passes checksum/media/duration/audio QA;
8. the UI reads the result back without inventing success.

## 11. Rollback and failure semantics

- page-only failure never changes canonical state;
- prepare without apply expires safely;
- apply failure shows the operation identity and recovery action;
- unknown external state is preserved and never blindly replayed;
- a later page cannot hide an earlier blocker;
- rollback uses the owning service's existing recovery contract, not a UI
  attempt to reverse domain state;
- reverting a Shell slice must leave Project/domain formats unchanged unless a
  separately authorized migration exists.

## 12. Critic review

### Builder Critic

Finding: implementing all pages in one PR would create broad Shell ownership,
poor fault isolation and repeated domain code. Resolution: P-UX-2A..E use a
single registry and slice by the real production flow while preserving domain
owners. Residual Critical/High/Medium: `0 / 0 / 0`.

### Security/Authority Critic

Finding: making mock buttons work by calling generic bridge methods could
inflate visual intent into execution authority. Resolution: every action binds
typed source/output identities and existing prepare/confirm/apply gates;
download/install authority does not imply license, Consent, publication,
Release or Production authority. Residual Critical/High/Medium: `0 / 0 / 0`.

### Operations/UX Critic

Finding: `V6.1.1_VISUAL_PARITY_PASS` can be mistaken for usable end-to-end
completion while 37 controls remain disabled. Resolution: the roadmap and UI
carry two independent states, and only the F0..F10 packaged vertical slice can
mint `MOCK_ABSOLUTE_FUNCTIONAL_EXPORT_FLOW_PASS`. Residual
Critical/High/Medium: `0 / 0 / 0`.

## 13. Judge

Decision: `PASS_FOR_ROADMAP_INTEGRATION / IMPLEMENT_SEQUENTIALLY`.

- Visual authority: `V6.1.1` HTML mock, unchanged.
- Current functional-flow state: `NOT_COMPLETE`.
- First runnable unit: `P-UX-2A`.
- Final completion token:
  `TASK036_MOCK_ABSOLUTE_FUNCTIONAL_EXPORT_FLOW_COMPLETE`.
- Release/Deploy/Production state: unchanged and not inferred.
