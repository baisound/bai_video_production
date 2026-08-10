# TASK-027 — AI Video Creation Studio / New Production Orchestrator

- Status: `PROPOSED / NOT AUTHORIZED`
- Governance candidate: `DEV-4 PRODUCT ORCHESTRATION CRITICAL`
- Product route: `NEW_VIDEO_CREATION`

## Objective

Provide a GUI-led workflow in which a user describes the video they want, reviews and revises an AI-generated production design, presses an explicit `GO` approval, and then lets the Product generate, validate, register and arrange the required visual, video and audio Assets into a human-editable DaVinci Resolve Timeline.

This is distinct from the existing `EDIT_EXISTING_VIDEO` route. Both routes converge on the same canonical Asset Registry, Edit Plan, Timeline Mapping, Resolve ownership, QA and manual-handoff contracts.

## User workflow

1. Open **New Video** in the GUI.
2. Complete a guided form covering purpose, audience, platform, aspect ratio, target duration, style/tone, story/message, characters/brand, references, narration, BGM/SE preferences, language, budget, deadline, rights constraints and output variants.
3. Request an AI production proposal.
4. Review an editable proposal containing concept, title/copy candidates, structure, script, storyboard, shot list, Asset plan, narration plan, SE/BGM plan, Timeline plan, model/provider choices, estimated generation time/cost and license/quality risks.
5. Revise individual fields manually or ask AI to revise selected sections. Every revision is versioned; rejected proposals remain historical Evidence and are never silently overwritten.
6. Press `GO`. The approved proposal becomes an immutable Production Plan snapshot. No paid or high-cost generation starts before this approval.
7. The orchestrator creates and validates image, video, voice, SE and BGM Assets, then assembles them through canonical placement plans into an Automation-owned Resolve Timeline.
8. Inspect preview/progress, pause or cancel at safe checkpoints, and retry/reconcile failed provider work without blindly duplicating external generation.
9. Replace any generated or supplied Asset manually. The replacement passes the same ingest/rights/checksum gates and invalidates only downstream outputs that actually depend on that slot.
10. Rebuild the affected shots/audio/timeline, then hand off to normal manual editing and final Render QA.

## GUI surfaces

- New Video wizard and reusable project templates;
- free-text intent plus structured form fields;
- reference upload/selection from canonical Assets;
- AI proposal editor with section-level regenerate, compare and restore;
- storyboard/shot-card editor with duration and dependency visibility;
- provider/model/cost/quality policy controls with safe defaults;
- explicit preflight and `GO` approval screen;
- job progress, pause/cancel/resume and actionable error recovery;
- Asset bin with generated/supplied badges, provenance and Replace action;
- Timeline preview and “rebuild affected range” action;
- final Resolve handoff, QA status and export controls.

The GUI may reuse TASK-021 operational components, but TASK-027 owns the creation-specific interaction and orchestration contract. It must not become a thin form that bypasses Product Jobs, permissions, Evidence or approval gates.

## Canonical contracts

### Creation Intent

A versioned user-intent document containing the form values, free-text request, reference bindings, constraints and requested outputs. Raw secrets are excluded from canonical Evidence.

### Production Proposal

An AI-authored but user-editable proposal containing:

- creative concept and audience promise;
- script/narration and scene structure;
- storyboard and exact shot list;
- per-shot visual/video generation or supplied-Asset requirements;
- SE, BGM, ambience and narration requirements;
- duration/aspect/framerate/output variants;
- provider/model selection policy;
- rights, safety, cost, resource and quality gates;
- dependency graph and estimated execution range.

### Approved Production Plan

The immutable snapshot created by `GO`. It binds proposal revision, canonical reference Assets, provider policies, cost ceiling and downstream generation/placement requests. Editing a proposal after `GO` creates a new revision and requires a new approval for changed work.

### Asset Slot and replacement

Every scene element uses a stable semantic slot such as `SCENE-03/HERO_VIDEO`, `SCENE-03/SFX-01`, `GLOBAL/BGM-BED` or `NARRATION/SEGMENT-04`. A slot may bind a generated Asset or a user-supplied canonical Asset. Replacement never mutates the old Asset; it creates a new binding revision and marks dependent previews, mixes and Timeline ranges stale.

## Orchestration

- TASK-004 supplies local image/video/audio runtime adapters, Character Identity and structured H3 briefs.
- TASK-013 owns creative/provider orchestration for generated image/video/SE/BGM Assets.
- TASK-014 owns narration/TTS and consent/voice contracts.
- TASK-022 owns exact source/Asset-to-Timeline mapping.
- TASK-026 owns SE/BGM/narration placement, beds, loops, fades and bounded snapping.
- TASK-010 owns Resolve assembly into an Automation-owned Timeline.
- TASK-011/012 own Render QA and manual handoff.
- TASK-020 supplies full resource admission and scheduling; TASK-021 may supply shared job/evidence UI components.

## Safety and control requirements

- `GO` is a mandatory human authorization boundary before external generation or Resolve mutation.
- Show estimated cost/time ranges and provider/license restrictions before approval.
- Enforce configurable total cost, per-provider retry and resource ceilings.
- Never auto-publish generated output.
- Never modify a human-owned Timeline.
- Preserve all proposal/approval/Asset-binding revisions and generation provenance.
- Validate every generated and replacement Asset before canonical registration or Timeline use.
- Reconcile resumable provider jobs; ambiguous external state fails closed.
- Support pause/cancel without corrupting the canonical plan or published Assets.
- Mark AI suggestions as proposals and retain manual override at every creative layer.

## Phased delivery

### Slice A — GUI proposal studio

New Video form, intent schema, proposal generation/editing/versioning, storyboard/shot cards, cost/rights preflight and `GO` snapshot. Uses mock/provider-neutral generation plans and performs no external generation by default.

### Slice B — visual generation vertical slice

Generate or accept supplied images/video for approved shot slots through TASK-004/013, register Assets, support replacement and rebuild only affected shots.

### Slice C — complete audio production

Generate/import narration, SE and BGM through TASK-013/014; create TASK-026 placement/bed plans and allow per-slot replacement.

### Slice D — one-click Resolve assembly

Compile the approved plan into TASK-022 mappings and TASK-010 Automation-owned Resolve Timeline, then run QA and handoff.

### Slice E — templates and optimization

Reusable channel/series templates, multi-format variants, learned proposal defaults and cost/quality optimization without weakening approval or rights gates.

## Acceptance criteria

1. A non-technical user can define a new video through GUI fields plus free text.
2. The Product returns a complete, editable and versioned production proposal before generation.
3. No external generation or Resolve write occurs before explicit `GO` approval.
4. Approved plans bind exact proposal revision, inputs, policies and cost ceiling.
5. Visual, video, narration, SE and BGM work is represented as a dependency graph of stable Asset slots.
6. Generated and user-supplied Assets use the same canonical validation, rights and provenance gates.
7. Users can replace any slot and rebuild only proven dependent outputs.
8. Provider retries/recovery are bounded and do not blindly duplicate paid work.
9. Final placement is frame/time exact and targets only an Automation-owned Timeline.
10. The result remains manually editable in Resolve and supports ordinary QA/handoff.
11. Proposal history, approvals, generation operations, replacement bindings and final assembly remain auditable.
12. End-to-end tests cover proposal correction, GO denial/approval, partial failure/resume, Asset replacement and Timeline rebuild.

## Dependencies and execution position

- Required foundation: TASK-001 through TASK-004.
- Slice A may start after its Task authorization and can proceed in parallel with TASK-022 design.
- Slice B requires the relevant TASK-013 visual/video orchestration slice.
- Slice C requires TASK-013, TASK-014 and TASK-026.
- Slice D requires TASK-022 and TASK-010.
- Full Production readiness also requires TASK-011/012 and the applicable TASK-020 resource controls.

TASK-027 is proposed by Owner direction but is not implementation-authorized by this document alone.
