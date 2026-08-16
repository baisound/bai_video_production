# TASK-036 P-UX-2 — V6.1.1 Element / Selection / Export Flow Re-audit

Date: `2026-08-17`
Audit base: `2e787b395a3de62ed3cb53547a1664cc42f6601f`
Effect: `READ_ONLY_BROWSER_AND_SOURCE_AUDIT`
Judge: `MODEL_TO_EXPORT_FLOW_NOT_CONNECTED`

## 1. Purpose

This re-audit compares every visible and interactive mock element with the
embedded runtime. It is deliberately broader than a button count. It checks
fields, selects, labels, tabs, cards, candidate lists, transport controls,
selected state, what happens after selection, canonical read-back and the
identity handed to the next page.

The V6.1.1 HTML mock remains the absolute visual and interaction-intent
authority. Its random progress, timers, sample records, local arrays and toast
messages are illustrative only and never Product Evidence.

## 2. Inventory result

| Measure | Mock | Runtime | Result |
|---|---:|---:|---|
| Primary pages | 14 | 14 | outer route present |
| Buttons | 253 | 126 | incomplete |
| Stable element IDs | 205 | 109 | incomplete |
| Select controls | 57 | 2 | incomplete; runtime selects do not choose generation models |
| Input / textarea controls | 83 | 7 | incomplete |
| Disabled runtime buttons | — | 37 | 36 have truthful reasons |

The outer layout, theme, stage bar and all primary destinations are present.
That visual result remains valid, but it does not prove the inner page content,
choice mechanics or production flow.

## 3. Page-by-page element and behavior matrix

| Page | Mock choice / action intent | Current runtime behavior | Missing closure |
|---|---|---|---|
| Home | choose/open Project and recent item | canonical empty/current Project state is shown | supported create/open/ingest result must refresh the same screen and bind exact Project/Asset IDs |
| Planning | enter brief/duration, choose AI Provider/model, proposal count, generate and select Proposal | only Proposal action is shown and disabled because typed Proposal service is absent | all fields/selects, Proposal list, Human selection and Approved Plan handoff |
| Scenes | choose Scene, edit timing/purpose/narration/visual/audio/continuity, add/remove/finalize | list projection exists; mutations are disabled with service reasons | editable Scene revision, validation, final frame-coverage receipt and next-page binding |
| WORLD LOCK | choose official image/detail, drop/reference, generate, compare, adopt/lock | search/kind projection and bounded Product truth exist | complete detail/edit/drop/history/compare/adopt surface and selected LOCK read-back |
| Scene Design | choose Scene tab, Character/Space/Composition, continuity, Start/End intent, prompts and audio direction | no interactive controls | entire 40-control surface and compiled Scene revision |
| Image Generation | choose Provider/model, prompt, candidate count and Candidate | no interactive controls | entire selection/generation/adoption path |
| Video Generation | choose Provider/model, count, duration, aspect, resolution, audio options, normalized prompt and Candidate | generate action is disabled; navigation only | canonical selectors, settings, prompt chain, admission, execution receipt and Candidate selection |
| Audio | choose/import Master SRT, narration, BGM, SFX, ambience and preferred results | only bounded Placement Plan entry is visible | generation/import choices, result selection, exact audio Asset and placement handoff |
| Asset Review | adopt/hold/reject a Candidate and build rough edit | actions appear only when a canonical Audit candidate exists; disconnected default has none | truthful empty guidance, complete Human decision UI and adopted Asset handoff; rough edit builder remains missing |
| Edit | choose track/clip/range/replacement and use transport/history/edit operations | canonical clip/track selection, seek, IN/OUT and some mutations exist | playback transport, replacement search/results, undo/redo/snap and remaining range/edit controls |
| Final Review | inspect QA, comment, revise/return or approve | typed Final Approval is disabled | aggregate readiness projection, comment/revise/return and exact Human approval receipt |
| Export | choose preset/destination, add queue Job, individually dispatch and inspect result | existing Jobs can be listed/prepared; preset and queue-add are disabled; Run All is intentionally forbidden | preset/destination binding, exactly-one Job creation, render QA and output read-back |
| Assets | select tags/result and set/insert/replace into Scene | reduced canonical Asset projection | tag truth plus exact target-bound set/insert/replace proposals and receipts |
| Quick | choose image/video/audio Provider/model, prompt/reference/seed and generate | only Quick Intent creation is shown and disabled | all 36 mock controls, compiled Prompt/rights/cost/admission, results and adoption |

Page-local interactive counts were `7/8, 7/1, 13/4, 13/4, 40/0, 10/0,
17/2, 19/1, 1/0, 85/32, 4/3, 7/7, 40/13, 36/1` for mock/runtime
from Home through Quick respectively.

## 4. Required selection contract

Every selector, card choice, tab, candidate and timeline selection must use the
same lifecycle:

```text
choice catalog snapshot
  -> exact selected coordinate
  -> visible selected state
  -> capability / rights / license / cost / resource / freshness validation
  -> typed prepare
  -> Human confirmation where required
  -> owning-service apply
  -> canonical receipt
  -> fresh same-screen read-back
  -> exact next-screen identity
```

The runtime must distinguish `LOADING`, `EMPTY`, `READY`, `BLOCKED`, `ERROR`,
`STALE`, `UNKNOWN` and `RECOVERY_REQUIRED`. A missing choice cannot silently
fall back to a different model. Selection does not grant Provider, paid,
download, model-load, publication, Release or Production authority.

## 5. Model selection to export trace

| Gate | Required proof | Current result |
|---|---|---|
| M0 Catalog | canonical Provider/model snapshot, mode and selected coordinate | `MISSING`; Settings is read-only and no generation selector exists |
| M1 Intent | Project/Scene/Prompt/reference binding | `PARTIAL`; canonical foundations exist, page fields/handoffs are incomplete |
| M2 Admission | capability, rights/license, cost, resource and freshness | `BACKEND_PARTIAL / UI_MISSING` |
| M3 Generation | prepare/confirm/apply plus durable execution receipt | `BLOCKED`; main generate actions are disabled |
| M4 Candidate | selected Candidate, Audit/Human decision and Asset adoption | `BACKEND_BOUNDED / UI_INCOMPLETE` |
| M5 Edit | target-bound insert/replace and persisted Timeline revision | `PARTIAL` |
| M6 Final Review | aggregate blockers and typed Human final approval | `MISSING` |
| M7 Queue creation | preset, destination and exactly-one durable Job | `MISSING` |
| M8 Dispatch | individual confirmation and durable dispatch state | `EXISTING_JOBS_ONLY` |
| M9 Output | artifact checksum/media/duration/audio QA and UI read-back | `UNIFIED_UI_MISSING` |

Overall Judge:

`BROKEN_AT_M0_AND_LATER_GATES / MODEL_TO_EXPORT_FLOW_NOT_CONNECTED`.

## 6. Updated implementation order

1. `P-UX-2A0 ELEMENT_SELECTION_CONTRACT_INVENTORY`: register every mock
   element and selection lifecycle; no effects.
2. `P-UX-2A1 MODEL_CAPABILITY_SELECTOR_PROJECTION`: connect canonical
   Provider/model choices and retained selected state; no Provider execution.
3. `P-UX-2B INTAKE_PLANNING_SCENES`: close Project, Proposal and Scene handoff.
4. `P-UX-2C GENERATION_AUDIO_ADOPTION`: close Scene Design, Image, Video,
   Audio, Candidate/Audit and Asset adoption under existing effect gates.
5. `P-UX-2D EDIT_FINAL_EXPORT`: close remaining Timeline operations, typed
   final approval, preset/destination, queue creation and output projection.
6. `P-UX-2E PACKAGED_VERTICAL_E2E`: prove restart-safe model-to-output flow in
   the packaged Windows application.

## 7. Completion criteria

Completion requires a supported fixture to retain the same canonical lineage:

```text
Provider/model
  -> Prompt/Project/Scene
  -> admission + explicit execution authority
  -> durable generation Job
  -> Candidate + Audit/Human decision
  -> adopted Asset
  -> persisted Timeline revision
  -> typed Final Approval
  -> exactly one Export Job
  -> individually confirmed dispatch
  -> verified output artifact and QA read-back
```

Each transition must be visible, keyboard-accessible, restart-safe and
fail-closed for stale/unknown state. The final token remains
`TASK036_MOCK_ABSOLUTE_FUNCTIONAL_EXPORT_FLOW_COMPLETE`; it is not established
by this audit.

## 8. Judge

Decision: `ROADMAP_UPDATE_REQUIRED / IMPLEMENT_A0_THROUGH_E`.

- visual shell parity remains accepted;
- element and interaction parity is not complete;
- model selection through export is not connected;
- no mock-only state may be promoted to Product success;
- current audit effect: `0`.
