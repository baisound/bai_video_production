# BAI VIDEO PRODUCTION — Product Workflow V6 Integration
# Development Handoff / Current Implementation Impact / Missing-Design Discovery Ver.1.0

## Document Control

- Date: `2026-08-14`
- Status: `OWNER_REVIEW_REQUIRED / PRODUCT_DESIGN_HANDOFF / NO_IMPLEMENTATION_AUTHORITY`
- Product snapshot supplied: `bai_video_production-main.zip`
- Package version in supplied snapshot: `0.20.1`
- GitHub archive comment marker: `8df313fec57d9913639e81a006faa016749ebb8f`
- Current-state recorded stable release: `v0.20.1`
- Current-state recorded roadmap: `Ver.1.44 / Addendum XXXVI`
- Current-state recorded next Consumer gate: `TASK-013 safe native-runtime resumption decision`
- Important: the current live repository MUST be revalidated before implementation. This handoff is not Canonical Authority.

---

# 1. Executive conclusion

The V6 / V6.1 / V6.1.1 Product design is not a greenfield UI proposal.

The current Product already has major foundations for:

- Unified Desktop Shell;
- Planning / Proposal / Human GO;
- Production Blueprint;
- Asset Registry / Scene Asset Slot;
- Candidate history;
- Human Audit;
- LOCK / STALE;
- Continuity;
- Prompt Registry / Generation Attempts;
- Generation Queue / Safety;
- Provider / Model routing;
- Windows Credential Manager;
- Audio Workspace / placement;
- Subtitle / Narration foundations;
- Resolve assembly / Render QA / Human handoff.

Therefore the receiving implementation team MUST first map every new requirement onto current code, schemas, stores, tests and Product tasks.

Do not create a second application, second lock lifecycle, second prompt-history store, second credential system, second generation queue or second audio-placement subsystem simply because the V6 mock presents a new UI.

At the same time, the current Domain Contract is not sufficient for several requirements now made explicit by real production use.

The largest known changes are:

1. Scene-level reference use must evolve to **Start Frame / End Frame specific reference binding**.
2. Character references must support multiple selections per frame; Space and Composition are single-selection per frame.
3. Start and End may intentionally use different people, different spaces and different camera/composition.
4. WORLD LOCK needs a first-class iterative candidate workflow without duplicating TASK-037/038/040 lifecycle semantics.
5. Visual Prompt Director needs a Product-owned service and traceable Japanese-source -> normalized-Japanese -> English-runtime prompt pipeline.
6. AI Video prompt compilation depends on BGM/SE/Ambience generation toggles and AI-proofreading state.
7. Audio needs Project Timeline / range semantics, not only Scene booleans.
8. Quick Generate needs a truthful authority model that does not fake Approved Plan/Human GO.
9. The Unified Desktop Shell needs substantial NLE/production UX expansion.
10. Export needs a real queue/application contract rather than a front-end-only progress list.

These are Domain/Application integration issues, not cosmetic changes.

---

# 2. Mandatory non-trust rule

The receiving team must NOT assume this handoff is correct or complete.

Use:

```text
Handoff / Mock / Real-production evidence
        ↓
Current repository audit
        ↓
Current Task / Schema / Store / Test mapping
        ↓
Contradiction + missing-source search
        ↓
Already-implemented / partial / missing classification
        ↓
Design-gap discovery
        ↓
Roadmap impact
        ↓
Complete detailed design
        ↓
Critic / Owner decision
        ↓
Implementation authorization
```

For each claim classify at minimum:

- `CONFIRMED_CURRENT`
- `ALREADY_IMPLEMENTED`
- `PARTIALLY_IMPLEMENTED`
- `NEW_CAPABILITY_REQUIRED`
- `CONTRACT_MIGRATION_REQUIRED`
- `SUPERSEDED`
- `CONFLICTS_WITH_CURRENT_CANONICAL`
- `UNVERIFIED`
- `OWNER_DECISION_REQUIRED`

“Nothing in the repository contradicts this handoff” is not sufficient.

The team must actively look for requirements not written here.

---

# 3. Current Product state that constrains the roadmap

The supplied current-state records:

- Product status: `V0_20_1_RELEASED`
- R3 control loop: complete
- R4 local Comfy adapter: hosted-closed
- safe runtime readiness preflight: hosted-closed
- native generation runtime: parked
- active Consumer Task: none
- next Consumer decision: TASK-013 safe native-runtime resumption
- stable release: `v0.20.1`

This is an advantageous insertion point for a cross-cutting Product workflow migration.

The Product should not resume real native generation using a reference/prompt/workflow contract that is already known to require structural revision.

---

# 4. Recommended roadmap insertion

Recommended:

```text
v0.20.1
TASK-036 minimum editing MVP complete
R2 Product Control promotion complete
R3 Continuity / Prompt control complete
R4 local adapter + readiness hosted-closed
Native H3 PARKED
        |
        v
V6 PRODUCT WORKFLOW RECONCILIATION GATE      <-- INSERT NOW
        |
        +-- independent current-main audit
        +-- requirement completeness review
        +-- existing implementation coverage map
        +-- full detailed design
        +-- exact roadmap/task split decision
        |
        v
V6-A VERSIONED CONTRACT MIGRATION
        |
        v
V6-B WORLD LOCK / FRAME REFERENCE BINDING
        |
        v
V6-C VISUAL PROMPT / GENERATION CONTROL
        |
        v
V6-D TIMELINE AUDIO / MASTER NARRATION
        |
        v
V6-E UNIFIED SHELL / QUICK GENERATE / EXPORT
        |
        v
V6-F NATIVE / UX / REGRESSION ACCEPTANCE
        |
        v
TASK-013 NATIVE H3 RESUMPTION DECISION
        |
        v
REAL PROVIDER / NATIVE GENERATION VALIDATION
```

This is a sequencing proposal only.

A new canonical Task identity must not be guessed from this document.

The detailed design must decide whether the work is:

- one cross-cutting Product Integration Task;
- multiple sequential tasks;
- a new integration task plus a revised not-yet-authorized TASK-041 Audio task;
- or another bounded allocation.

Completed TASK-036/037/038/039/040 should not be rewritten as if they were incomplete. Their contracts are reuse inputs.

---

# 5. Current implementation surfaces to reuse

## 5.1 TASK-027 — Planning / Production Blueprint

Current source includes:

- `production_blueprint.py`
- `planning_application.py`
- `planning_workspace.py`
- Approved Plan / Proposal / Scene Ledger / Generation Queue foundations

Current `BlueprintScene` contains scene-level:

```text
reference_ids[]
audio
locked_reference
```

and Blueprint serialization currently emits:

```text
blueprint_version = 1.0.0
```

This is the primary migration surface for frame-specific binding.

---

## 5.2 TASK-037 — Production Control

Current source includes:

- `SceneAssetSlot`
- Candidate history
- `LOCKED`
- `STALE`
- dependency graph

Current `SlotKind` includes:

```text
START_FRAME
END_FRAME
VIDEO
VFX
SE
BGM
NARRATION
OTHER
```

WORLD LOCK must reuse this lifecycle or an explicitly evolved version of it.

Do not create an independent `locked=true` JSON registry.

---

## 5.3 TASK-038 — Audit

Human Candidate decision remains separate from AI score and separate from LOCK.

Preserve:

- Reject != Delete
- NEEDS_REGENERATION != Generate
- ACCEPT != LOCK
- AI score != Human Final Authority

---

## 5.4 TASK-039 — Continuity

Preserve exact `DIRECT_CONTINUATION` semantics.

Previous End Asset must be reused as the next Start Asset where the boundary is DIRECT.

Do not regenerate a visually similar Start Frame.

---

## 5.5 TASK-040 — Prompt Registry / Generation Evidence

Reuse:

- immutable Prompt version;
- Prompt SHA/body reference;
- Provider Profile binding;
- input Asset hashes;
- Generation Attempt / parent Attempt;
- failure code;
- regeneration strategy.

Visual Prompt Director must publish into this existing history/evidence model rather than create a parallel prompt database.

---

## 5.6 TASK-013 — Shot Feasibility / Visual Compliance / Creative Generation

Reuse:

- Shot Feasibility;
- Scene-compatible reference roles;
- local generation safety;
- Provider execution boundary;
- local ComfyUI adapter;
- safe runtime readiness.

Do not resume parked Native H3 only because the new UI has an AI Video button.

The native execution decision remains separate.

---

## 5.7 TASK-028 / 032 / 033 / 034 — Provider, Model and Secret

Reuse:

- `ModelRoute`
- Provider / model / workload / capabilities
- adapter implementation status
- credential refs
- Windows Credential Manager

The new Provider -> Model two-stage selector should be a projection of current configuration/catalog truth.

Do not hard-code a second Provider/Model JSON as canonical unless the independent audit proves the current registry cannot express the required product capability.

---

## 5.8 TASK-041 / Audio foundations

Current Product already contains Audio Workspace / placement foundations.

The detailed design must decide how much of the new Timeline audio model belongs to TASK-041 versus the cross-cutting V6 integration task.

Do not treat Scene `bgm: bool` as the final placement source of truth.

---

## 5.9 TASK-036 — Unified Desktop Shell

V6 is an expansion of the existing Product Shell.

Do not create a separate V6 desktop application.

Reuse current:

- Shell command authority;
- project revision;
- one-shot confirmation;
- stale rejection;
- background jobs;
- recovery;
- packaged desktop entrypoint.

---

# 6. Required Product behavior — Scene Design / Start-End

## 6.1 Binding location

Character / Space / Composition Lock selection belongs to each frame intent, not the Scene as one shared binding.

```text
Scene
├─ Start Frame Intent
│  ├─ Character Lock IDs [0..N]
│  ├─ Space Lock ID      [0..1]
│  └─ Composition Lock ID[0..1]
│
└─ End Frame Intent
   ├─ Character Lock IDs [0..N]
   ├─ Space Lock ID      [0..1]
   └─ Composition Lock ID[0..1]
```

In guided/locked mode, Space and Composition will normally have a single selected item.

Expert/direct mode may intentionally omit locks; exact required/optional rules are a detailed-design decision.

## 6.2 Start and End are allowed to differ

Valid examples:

- Start = one person / End = four people
- Start = inside / End = outside
- Start camera = door-facing / End camera = exterior-view
- Start and End may use different Composition Lock
- Start and End may use different Space Lock

Do not implement a hidden assumption that all Lock selections must be identical between the two frames.

## 6.3 Character multiplicity

Character is not a scalar.

Use an ordered/set-like collection with explicit identity references and no accidental duplicates.

The detailed design must define:

- ordering semantics;
- role of each character;
- primary subject if needed;
- provider reference mapping;
- audit cardinality checks;
- what happens if Character availability changes.

---

# 7. WORLD LOCK iterative workflow

The real workflow requires repeated generation before a reference is good enough.

UI must support:

```text
Generation 01
  A B C D
Generation 02
  A B C D
...
Generation 20
```

and:

- candidate comparison;
- reject/hold/adopt;
- Human official Lock;
- previous generations remain visible;
- changing the official Lock marks dependent outputs as STALE/review-required;
- no automatic destructive deletion.

Candidate history and Human decision must reuse current Production Control/Audit/Prompt foundations.

The detailed design must decide whether current `SlotKind` is extended with reference roles such as:

- `CHARACTER_REFERENCE`
- `SPACE_REFERENCE`
- `COMPOSITION_REFERENCE`

or whether another existing structure is safer.

Do not choose this from the mock alone.

---

# 8. Composition / Final Shot reference

Composition Lock is not merely “same room.”

The detailed design must preserve:

- Task Axis;
- Visibility Contract;
- Depth Order;
- Camera position;
- lens/framing;
- must-show / must-not-show;
- scene-compatible final-shot reference;
- Shot Feasibility before downstream generation.

Room master/reference and Scene final-shot/composition reference are different roles.

---

# 9. Visual Prompt Director

Visual Prompt Director is a required Product design input.

It should not become fourteen mandatory user fields.

Internal reasoning includes:

- WORLD
- BEFORE
- NOW
- TRACE
- PHYSICS
- PLACE
- OWNER
- SUBJECT
- SPACE
- OFF-SCREEN
- CAMERA
- LIGHT
- FRAME
- AFTER

Product UI should expose only useful structured controls and an Advanced prompt view.

## 9.1 Prompt layers

Recommended Product model:

```text
Japanese Source Prompt
        ↓
Visual Prompt Director
        ↓
Normalized Japanese Prompt
        ↓
AI Proofreading / Translation
        ↓
English Runtime Prompt
```

The English Runtime Prompt is normally the text sent to an image/video model when the target Provider works better with English.

The original Japanese remains the Source.

Do not overwrite all layers into one mutable string.

Trace:

```text
source_ja_ref / hash
normalized_ja_ref / hash
runtime_en_ref / hash
proofreading state
manual English override state
```

should connect to TASK-040 Prompt version/Attempt history.

Raw prompt bodies should not be unnecessarily duplicated into general Evidence.

---

# 10. AI Video Prompt compilation

The UI order is semantically important.

```text
☐ BGM生成
☐ SE生成
☐ 環境音生成

☑ AI校正

Japanese Source Prompt
Normalized Japanese
English Runtime Prompt
```

BGM/SE/Ambience toggles appear above the prompt because their state changes the compiled prompt.

The compiler input should include:

- visual intent;
- Narration intent;
- Music Direction;
- SE Intent;
- Ambience Intent;
- generate_bgm;
- generate_se;
- generate_ambience;
- ai_proofreading_enabled;
- provider/model capability.

Toggling these changes Prompt version/hash.

Old Candidates remain traceable to the old Prompt version.

## 10.1 Narration / Sound Intent

Scene:

- Narration
- Music Direction
- SE Intent
- Ambience Intent

are inputs to AI Video prompt compilation where the selected model/capability uses them.

They are not necessarily Start/End still-image prompt fields.

---

# 11. Provider -> Model

Product UI:

```text
Provider [ ... ]
Model    [ models supported by selected Provider + required capability ... ]
```

Model options must be filtered by current route/catalog truth.

At minimum consider:

- provider;
- model;
- workload;
- enabled;
- capabilities;
- adapter implementation;
- credential availability;
- cost class;
- local/cloud mode.

Catalog listing alone must not imply runtime readiness.

---

# 12. Settings / Secret

The Settings view should list all Product-supported adapters vertically.

Each row distinguishes:

- adapter supported;
- adapter implemented;
- credential required;
- credential registered;
- connection checked;
- runtime usable.

Secret values are never re-displayed.

Use existing credential storage.

---

# 13. Quick Generate

Quick Generate is an Expert path.

Required modes:

- Image
- Start/End
- Video
- Audio

## 13.1 Reference inputs

Image:
- multiple reference images

Start/End:
- multiple reference images
- Character/Space/Composition Lock controls exist here

Video:
- Start image 1
- End image 1
- Negative Prompt

Audio:
- Prompt
- Negative Prompt
- reference input where provider supports it

Common reference sources:

- File
- Asset Library
- Generation Results

## 13.2 Authority

Quick Generate MUST NOT fake:

```text
plan_approved = true
```

A separate explicit quick-generation intent/session/authorization or equivalent contract is required if current Approved Plan binding cannot represent this path.

Quick output can be previewed/used as a Candidate, but Production adoption must still enter canonical Asset/Candidate/Audit/Lock flow.

---

# 14. Generated result as reference

A generated result does not have to be a user-favorited Library item before it can be used as another generation reference.

However it still needs canonical internal identity:

- candidate/asset ID;
- checksum;
- generation attempt;
- rights/provenance;
- provider/model;
- reference role.

UI “favorite/register in Asset Library” is separate from internal trace identity.

---

# 15. Audio Production — Timeline-level model

Real production requires parallel audio lanes after overall Scene timing is known.

Do not make all audio a child workflow of individual Scenes.

Required concepts to design:

```text
MusicPlan
AudioCue
AudioRange
NarrationCue
PlacementPlan
```

## 15.1 BGM

Support:

- one full-video BGM;
- multiple BGM sections;
- imported BGM;
- generate from Timeline IN/OUT;
- edit/trim/stretch/crossfade to target range.

BGM does not have to align with Scene boundaries.

## 15.2 Narration

Expected flow:

```text
Scene Narration Scripts
→ Master Narration Cue set / Master SRT projection
→ Narration generation
→ placement by cue timing
```

Some Scenes have no narration.

## 15.3 SE

Cue/time-oriented.

## 15.4 Ambience

Range-oriented.

## 15.5 Important unresolved source-of-truth decision

The receiving detailed design MUST decide how timing changes propagate.

Do not silently decide between:

- Scene/Production Timeline remains authoritative and Master SRT is derived;
- Master SRT can become an editable timing authority;
- bidirectional update with conflict state.

Conflict and migration rules are required before implementation.

---

# 16. Unified Editor behavior

The HTML mock is a reference, not proof of correct implementation.

## 16.1 Left / right panel

Header, tab, search and contents must not overlap.

Scrollable content area must receive remaining height.

Test actual window sizes/DPI.

## 16.2 Playhead

Generic Timeline behavior:

Ruler:
- click -> seek
- drag -> scrub

Empty Track lane:
- click -> seek

Playhead:
- direct drag -> scrub

Horizontal timeline:
- scrollbar and supported horizontal scroll interaction

Generic Clip:
- click -> select Clip / update Inspector
- **do not move Playhead**

Important existing-contract exception:

TASK-036 Cut Candidate Review may have its own selection/seek behavior.

Do not use one click handler for generic Clips and Cut Candidate overlays.

## 16.3 Long Timeline

Use a real time-scale model such as:

```text
pixels_per_second
```

Support:

- Fit Entire Timeline
- Zoom in/out
- selected-range fit
- horizontal scroll
- vertical scroll
- adaptive time ruler

Two-hour projects must remain operable.

## 16.4 Tracks

Dynamic:

- Video
- Subtitle
- Audio/Narration
- SE
- BGM

Add/remove with minimum required category rules.

Track state:

- visible
- lock
- mute/solo where relevant
- height

---

# 17. Top menus

Detailed design must specify actual commands and command authority.

Expected categories include:

## Edit
- Undo/Redo
- Cut/Copy/Paste/Delete/Duplicate
- split
- replace selected clip
- Set IN/OUT/Clear
- snap
- selection commands

## View
- Timeline Fit
- selected range fit
- Viewer/Asset/Inspector/Timeline/Jobs panels
- track height
- Viewer zoom
- full-screen Viewer
- reset panel layout

## Project
- Project info
- production summary
- Scene list
- Production Timeline Contract
- WORLD LOCK registries
- Asset Library
- Generation History
- Master SRT
- Music Plan
- Production Profile
- project validation / STALE dependency state

## Generate
- Quick Generate
- reference generation
- Start/End
- Video
- Narration
- BGM
- SE
- Ambience
- selected Scene/Clip/range generation
- Generation History
- Background Jobs

Each command must map to existing/new Application Service authority rather than mutate stores directly from JavaScript.

---

# 18. Export Queue

Required UX:

- Add to queue
- progress bar
- percentage
- per-job execute
- queue execute all
- stop/cancel where safe
- remove
- output destination
- open result/folder after completion

Required design:

Each queued job binds to:

- Project identity
- Timeline identity
- Edit/Assembly Plan hash
- export preset
- output target
- confirmation/authority context

If Project/Timeline/Plan changes, pending job becomes STALE or requires re-prepare.

`Execute all` must not silently bypass job-level external-mutation authority.

Reuse current render/QA commands.

---

# 19. Background Jobs

Use the existing Shell Background Job model where possible.

Do not make an unrelated front-end-only counter for:

- image generation;
- video generation;
- narration;
- BGM;
- SE;
- ambience;
- export.

The detailed design must decide common vs provider-specific job state.

---

# 20. Additional missing-feature candidates the design team must actively investigate

These are NOT assumed requirements. They are review prompts.

- Project migration UI and rollback/recovery for Blueprint vNext.
- Production Profile persistence and boundaries.
- UI layout profile vs Project semantic data separation.
- keyboard shortcuts.
- undo/redo semantics across Timeline and generation-related changes.
- large Asset Library virtualization/search performance.
- long-video performance and memory.
- autosave/crash recovery boundaries.
- generation cost estimate/budget preview.
- offline/local versus cloud readiness.
- Provider parameter capability forms.
- reference strength/weight model differences.
- multi-character role/order semantics.
- prompt/lock conflict detection.
- STALE propagation visualization.
- generation history compare UX.
- accessibility / keyboard navigation / Narrator.
- file picker and Windows path behavior.
- mixed DPI / multi-monitor.
- telemetry/privacy/redaction.
- generated-media rights/provenance.
- destructive Asset deletion/retention.
- project backup/portable handoff.
- Resolve/Premiere/External NLE export contract compatibility.

The receiving team must add other gaps discovered in current main.

---

# 21. No completed-task rewrite

Do not rewrite historical completion records to make V6 appear to have been planned all along.

Preferred pattern:

- preserve historical TASK evidence;
- create a new integration/design authority;
- cite completed foundations;
- evolve schemas/contracts with versioning;
- add new Evidence.

TASK-041 is currently not completed and may be a valid future owner for some Audio work, but the exact boundary must be decided in detailed design.

---

# 22. Mandatory implementation order

## Gate 0 — Revalidation / Roadmap Reconciliation

- verify current live main
- git status / branch / HEAD / remote
- Registry / current-state / roadmap
- exact task statuses
- full source-impact map
- source curation
- Design Gap Register
- roadmap/task split Owner decision

## Gate A — Versioned Domain Contract Migration

- `StartFrameSpec`
- `EndFrameSpec`
- `FrameReferenceBinding`
- cardinality/role rules
- Blueprint vNext schema
- old Blueprint read compatibility
- migration
- rollback
- Approved Plan/hash impact
- STALE/dependency impact
- cross-store validation

No full UI implementation before this contract is accepted.

## Gate B — WORLD LOCK / Reference

- candidate lifecycle projection
- Character/Space/Composition roles
- generation history
- comparison
- Human official Lock
- dependency/STALE
- DIRECT continuity

## Gate C — Visual Prompt / Generation

- VisualPromptDirectorService
- PromptCompilationService
- JA/JA-normalized/EN layers
- AI proofreading
- audio toggles
- Provider/Model selection
- capability filtering
- generated reference inputs
- Quick Generate authority
- Generation queue/jobs

## Gate D — Audio Timeline

- Master narration cues / SRT
- whole/range BGM
- SE cue
- Ambience range
- placement
- rough edit binding

## Gate E — Unified Desktop / NLE / Export

- navigation/menu
- panel groups
- Asset/History/Replace
- timeline interactions
- zoom/fit/scroll
- tracks
- Viewer
- generation drawers
- Export Queue

## Gate F — Acceptance / Regression

- full pytest
- compileall
- diff-check
- schema migration roundtrip
- cross-store validation
- crash/recovery
- stale confirmation
- secret redaction
- 2h Timeline
- actual click/drag/scroll
- panel clipping
- DPI/multi-monitor
- accessibility
- no dead controls
- DIRECT_CONTINUATION exact identity
- background jobs across navigation/restart
- export queue authority
- packaged Windows acceptance

## Gate G — Native generation resume decision

Only after the new reference/prompt/authority contract is accepted should the Owner decide whether/how to resume parked TASK-013 native H3.

Never replay the preserved uncertain execution automatically.

---

# 23. Required detailed design before coding

The next team must write complete detailed design covering at least:

1. current implementation audit
2. user workflow
3. Domain model
4. schema/versioning
5. migration/backward compatibility
6. persistence
7. Application Services
8. command/capability mapping
9. reference roles
10. Lock/Candidate/Audit lifecycle
11. STALE/dependency rules
12. continuity
13. Prompt compilation/versioning
14. Provider capability mapping
15. credential/security
16. Quick Generate authority
17. paid/cost controls
18. audio timing model
19. Master SRT timing authority decision
20. Timeline/Edit state
21. Export queue
22. background jobs
23. error/retry/idempotency
24. unknown-state handling
25. crash/recovery
26. observability
27. rights/provenance
28. UI/interaction contract
29. accessibility
30. performance
31. regression
32. native acceptance
33. rollout/canary
34. rollback
35. docs/roadmap/current-state synchronization
36. exact allowed files/test slice

If the handoff did not mention one of these, that is not a reason to omit it.

---

# 24. Handoff artifact authority

Priority when implementation begins:

1. Current live repository + current Canonical docs
2. Owner-approved new detailed design
3. Explicit user Product requirements
4. Real-production evidence
5. This handoff
6. HTML mock
7. illustrative diagrams/examples

The HTML mock is required because it communicates interaction intent, but it is not executable Product truth and not native acceptance evidence.

---

# 25. Final instruction

The correct next action is:

> **Do an independent current-main audit, discover omissions, redesign the roadmap if necessary, produce the full detailed design for all accepted V6 capabilities, obtain review/Owner approval, then implement as modifications to the existing BAI VIDEO PRODUCTION architecture.**

Do not begin by copying the mock into `task036_shell_ui.py`.

Do not begin by adding new JSON stores for features whose lifecycle already exists.

Do not resume native generation first.

The Product already has valuable foundations. V6 should integrate and evolve them rather than replace them.
