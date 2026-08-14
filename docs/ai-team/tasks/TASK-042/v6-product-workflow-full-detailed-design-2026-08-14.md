# TASK-042 — V6 Product Workflow Full Detailed Design

Status: `IMPLEMENTATION_READY_AFTER_ROADMAP_MAIN_MERGE`

Baseline: `8d055773f3966e301badff28e565ffcf26578721`

## 1. Architecture decision

V6 is one cross-cutting Product Integration Task with sequential, separately closed slices. Existing Task ownership remains authoritative for its lifecycle; TASK-042 composes and evolves those contracts. No completed Task is rewritten and no second Product application is created.

```text
Blueprint v2 / frame bindings
  -> TASK-037 Candidate/LOCK/STALE
  -> TASK-038 Human Audit
  -> TASK-013 Feasibility
  -> TASK-039 Continuity
  -> TASK-040 Prompt/Attempt
  -> TASK-027 Queue admission
  -> TASK-013 separately authorized execution
  -> TASK-036/041/010/011/012 Product UX and delivery
```

## 2. Domain model — Blueprint v2

### 2.1 Version

- Existing `ProductionBlueprint 1.0.0` remains immutable and readable.
- New contract is `ProductionBlueprint 2.0.0` because frame-binding semantics are incompatible with Scene-level references.
- The public parser accepts exactly 1.0.0 and 2.0.0. Unknown major/minor/fields fail closed.
- Canonical and packaged schemas remain byte-equivalent.

### 2.2 FrameReferenceBinding

```text
FrameReferenceBinding
  character_locks[]  ordered, unique Candidate/Asset bindings
    role: PRIMARY | SUPPORTING | BACKGROUND
    asset_id, asset_sha256, slot_id, candidate_id
  space_lock?        exactly zero or one
    asset_id, asset_sha256, slot_id, candidate_id
  composition_lock?  exactly zero or one
    asset_id, asset_sha256, slot_id, candidate_id
```

Every binding is an identity reference, not embedded media or a second lock flag. A referenced Candidate must be `LOCKED/CURRENT` in TASK-037 at production use time. Character ordering is presentation/provider order; duplicate Candidate, Asset or role-index identity is rejected. PRIMARY is optional but at most one.

### 2.3 FrameIntent

```text
FrameIntent
  frame_kind: START | END
  visual_intent
  task_axis_target
  required_visible[]
  forbidden_visible[]
  depth_order[]
  camera_semantic
  lens_framing?
  binding: FrameReferenceBinding
```

Start and End are independently valid and may intentionally differ. Guided production may require Space/Composition; Expert mode may omit them but receives explicit feasibility blockers rather than silent approximation.

### 2.4 BlueprintSceneV2

Scene v2 retains frame range, narrative role, source strategy, risk, camera motion, audio intent, post-composite text and final hold. It replaces Scene-level `reference_ids`/`locked_reference` with mandatory `start_frame_intent` and `end_frame_intent`. Scene audio remains intent only and never becomes placement truth.

## 3. Migration and backward compatibility

### 3.1 Preview only

`BlueprintV1MigrationService.preview()` reads and verifies the exact v1 document and creates an immutable checksummed proposal. Legacy `reference_ids` are not silently copied into Start and End because their role and frame applicability are ambiguous.

Each Scene becomes `NEEDS_FRAME_BINDING_REVIEW` with:

- preserved legacy IDs;
- deterministic proposed roles only where current registry kind proves them;
- unresolved Character/Space/Composition/frame decisions;
- source v1 checksum and target v2 checksum candidate;
- no store write and no GO authority.

### 3.2 Apply

Apply requires:

- exact source snapshot checksum still current;
- all Scene decisions completed;
- one-shot Human confirmation bound to the preview checksum;
- atomic append of a new Proposal revision containing v2;
- the v1 snapshot retained as rollback source;
- old Approved Plan marked stale, never edited in place;
- new Human GO and reference binding before queue admission.

Rollback means selecting the preserved v1 Proposal revision as the active design through a new explicit revision; it never deletes the v2 revision or rewrites history.

### 3.3 Hash and state impact

Blueprint checksum, Proposal checksum, Approved Plan checksum, Planning snapshot, feasibility Evidence, Prompt input hash, Queue admission and pending Export identity all change. Any downstream item bound to the previous chain becomes `STALE` or blocked for re-prepare. Existing completed outputs remain historical Evidence.

## 4. WORLD LOCK and reference roles

WORLD LOCK is a Product workspace/projection over existing stores:

- TASK-037 owns Candidate lifecycle and official Lock.
- TASK-038 owns Human decisions.
- TASK-040 owns Prompt/Attempt history.
- TASK-003 owns Asset identity/checksum/rights.

Production Control evolves with additive Slot roles `CHARACTER_REFERENCE`, `SPACE_REFERENCE`, `COMPOSITION_REFERENCE`. Old Slot values remain readable. Migration is append-only and unknown roles fail closed. Generation 01..N is a Prompt/Attempt/Candidate history projection. Reject/Hold/Accept/Lock remain distinct; replacement marks dependents stale and never deletes prior media.

## 5. Continuity

- `DIRECT_CONTINUATION`: next Start `asset_id` and `asset_sha256` must equal previous End. No Human override or similar-image regeneration exists.
- `CUT`: Start/End and adjacent bindings may differ.
- `MATCH_CUT`/soft continuity: current TASK-039 Human review path is retained.
- Changing an End frame stales a DIRECT-dependent Start and every downstream Prompt, Queue, Candidate, Audio/Timeline and Export identity derived from it.

## 6. Shot Feasibility and Composition

Before generation, the combined frame intent must verify:

- Task Axis before camera placement;
- required visibility and forbidden visibility;
- exact depth order;
- furniture/space integrity;
- scene-compatible Final Shot Reference, distinct from a Room Master;
- provider reference-role capability;
- DIRECT identity where applicable.

The standard production strategy is: empty Final Shot Reference -> feasibility PASS -> Character injection -> identity/geometry QA -> Candidate. Two repeated identical structural failure codes stop prompt micro-tuning and require layout/pose/depth/reference/provider strategy review.

## 7. Prompt architecture

`VisualPromptDirectorService` normalizes structured WORLD/BEFORE/NOW/TRACE/PHYSICS/PLACE/OWNER/SUBJECT/SPACE/OFF-SCREEN/CAMERA/LIGHT/FRAME/AFTER inputs without exposing fourteen mandatory fields.

`PromptCompilationService` creates an immutable body-private manifest:

```text
source_ja_ref + sha256
normalized_ja_ref + sha256
runtime_en_ref + sha256
proofreading_state
manual_override_state
frame binding hashes
narration/music/SE/ambience intent hashes
generate_bgm / generate_se / generate_ambience
provider profile/version/capabilities
negative prompt ref/hash
```

Changing any compiler input creates a new version. The runtime body is not copied to general Evidence. TASK-040 remains the Prompt/Attempt registry and receives only references/hashes and exact input identities.

## 8. Provider, Model and credential projection

Provider and Model lists derive from current `ModelRoute` and availability:

- enabled route;
- workload and required capability;
- adapter implementation/readiness;
- credential availability without displaying a secret;
- cost class and local/cloud mode.

Catalog presence is not runtime readiness. No second provider JSON is canonical. Secret rows reuse TASK-034 and display only supported/implemented/required/registered/checked/usable states.

## 9. Quick Generate authority

Quick Generate uses a versioned `QuickGenerationIntent`, not an Approved Plan. It binds mode, references, provider capability, prompt hashes, cost ceiling and one-shot execution decision. It never sets `plan_approved=true`.

- Image: multiple references.
- Start/End: multiple references and typed locks.
- Video: exactly one Start and zero/one End plus negative prompt.
- Audio: reference only when capability supports it.

Outputs receive internal Asset/Candidate/Attempt/provenance identity even if not favorited. Production adoption requires an existing/new Scene Slot, Human Audit, ACCEPT and LOCK. A Quick output never bypasses those gates.

## 10. Audio timing Source of Truth

The authoritative timing model is the Product/Production Timeline. Master SRT is a deterministic projection and exchange artifact.

- Direct Master SRT editing creates a `NarrationTimingChangeProposal`.
- Apply requires exact Timeline revision, conflict-free cue mapping and Human confirmation.
- Applied timing produces a new Timeline/Plan revision; the SRT is regenerated.
- Conflicting Scene/Timeline/SRT revisions become `TIMING_CONFLICT`; no last-writer-wins.

TASK-042 owns `MusicPlan`, `AudioCue`, `AudioRange`, `NarrationCue` and `PlacementPlan` integration. TASK-041 remains the Human placement review service. TASK-026 remains execution-plan compiler ownership and TASK-014 remains paid narration execution ownership.

Supported semantics:

- full-project or multiple-range BGM;
- imported or generated BGM;
- IN/OUT, trim/stretch/crossfade proposals;
- narration cue set with optional silent Scenes;
- SE point cues;
- ambience ranges;
- exact Timeline revision and Asset checksum binding.

## 11. Unified Shell and command authority

The existing trusted launcher and one Desktop entrypoint remain. New workspaces are presentation modules over Application Services, not direct JSON mutation.

Command categories remain `READ_ONLY`, `LOCAL_REVERSIBLE`, `LOCAL_DURABLE`, `HUMAN_FINAL_AUTHORITY`, `EXTERNAL_MUTATION`. Prepare/apply pairs are mandatory for migration, Lock, Prompt publish, Quick execution, Timeline timing apply, Export execution and destructive retention.

Generic Clip click selects without seeking. Ruler/empty lane/playhead seek or scrub. Existing Cut Candidate behavior remains an explicit exception. Project-semantic Timeline state is separated from UI layout/selection profile.

## 12. Timeline, performance and accessibility

- one `pixels_per_second` transform drives ruler, clips, playhead and scroll;
- Fit Entire, Fit Selection, zoom and horizontal/vertical scroll use the same transform;
- two-hour Timelines and large histories use windowing/virtualization;
- thumbnails load bounded and cancellable;
- track add/remove obeys minimum required categories;
- keyboard focus, labels, Narrator, 100/150/200% DPI, mixed-monitor and narrow-window layout are native acceptance cases.

## 13. Export Queue

Each durable queue item binds project, Timeline revision/hash, Edit/Assembly Plan hash, preset, output target, authority class and prepared confirmation context. A changed identity makes pending work `STALE_REPREPARE_REQUIRED`.

`Execute All` iterates jobs through their individual authorization contract; it does not create blanket external-mutation authority. State includes prepared/running/succeeded/failed/cancel-requested/cancelled/unknown/stale. Unknown external dispatch is never automatically retried. Render QA and output-open reuse TASK-011/TASK-036 commands.

## 14. Background Jobs and restart

Existing `BackgroundJobRegistry` becomes the shared projection for local/provider generation, audio derivation and export. Durable provider/export state remains in owning stores. On restart, Product classifies exact terminal/known-failure/unknown-dispatch/stale; UI counters never invent completion.

## 15. Persistence, atomicity and recovery

- bounded JSON size and strict parsing;
- atomic temp/write/fsync/replace through existing writers;
- serialized compare-and-swap;
- one active mutation lease per store/cross-store operation;
- journal before first multi-store mutation;
- prepared/committing/completed/abandoned recovery with exact checksums;
- no symlink/path escape;
- no secret, host path or raw private Prompt in general Evidence.

## 16. Security, rights and cost

- paid or credential-bearing execution requires exact current authorization and budget/cost preview;
- local/free is still a side effect and requires its configured execution gate;
- Provider timeout with unknown state is recovery-required/no replay;
- generated media and references bind provider/model, input assets, rights/provenance and retention;
- Delete is separate from Reject and uses retention/destructive authority;
- external file input uses allowlisted Product path handling;
- prompt/privacy/redaction applies before persistence or egress.

## 17. Observability and learning

Record body-free metrics for attempts-to-Lock, feasibility failure, structural failure recurrence, Prompt override, provider/model failure, Human correction, queue failure, audio placement correction and dead-control regression. Metrics create proposals/Evidence only and never change Product behavior automatically.

## 18. Rollout and release

- No release version is selected now.
- Each slice merges through a dedicated PR from current main and cleans its branch/clone.
- Blueprint v2 begins behind explicit migration/use, while v1 remains readable.
- Old project open/read and no-op save must remain valid.
- Native/user-facing completion requires actual packaged Windows Evidence, not mock/hosted-only claims.
- Exact semver/tag/release is a P-V6-6 decision after actual compatibility and acceptance Evidence.

## 19. Gate sequence and exit criteria

### P-V6-1 Contract Migration

- v1 unchanged and readable;
- closed v2 schema/domain;
- explicit unresolved migration preview;
- no silent apply or GO;
- deterministic checksums and schema parity;
- focused/full regression and Critic 0/0.

### P-V6-2 WORLD LOCK

- typed reference roles reuse Candidate/Audit/Prompt;
- Human official Lock and stale propagation;
- DIRECT exact identity;
- restart/cross-store recovery.

### P-V6-3 Prompt/Generation/Quick

- JA/JA/EN immutable compilation;
- provider/model capability projection;
- quick authority and production adoption boundary;
- no paid/native claim without Evidence.

### P-V6-4 Timeline Audio

- Timeline-authoritative Music/Cue/Range/Placement;
- SRT proposal/conflict flow;
- TASK-041 review reuse;
- no Provider/TASK-026/Resolve/Cubase side effect unless separately authorized.

### P-V6-5 Unified Shell/Export

- no dead controls;
- exact command authority;
- 2h Timeline and dynamic tracks;
- durable stale-safe Export Queue.

### P-V6-6 Acceptance

- migration round-trip/rollback;
- cross-store/restart/crash/stale/security regression;
- full Windows/WSL/hosted suites;
- real click/drag/scroll, DPI/multi-monitor/accessibility;
- packaged shell/background/export Evidence;
- then separate TASK-013 Native H3 decision.

## 20. P-V6-1 exact Allowed Files

The first implementation slice after roadmap merge is limited to:

- `src/ai_video_production/production_blueprint_v2.py` (new)
- `src/ai_video_production/blueprint_v2_migration.py` (new)
- `schemas/production-blueprint-v2.schema.json` (new)
- `src/ai_video_production/schema_resources/production-blueprint-v2.schema.json` (new identical copy)
- `tests/test_task042_production_blueprint_v2.py` (new)
- `tests/test_task042_blueprint_v2_migration.py` (new)
- `tests/test_schema_contracts.py` only if schema-discovery coverage requires it
- `docs/ai-team/tasks/TASK-042/**`
- `PROJECT.md`, `docs/ai-team/current-state.md`, `docs/ai-team/task-index.md`, `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md`, `CHANGELOG.md` for bounded status synchronization

P-V6-1 may read but must not modify the v1 domain/schema/store or any TASK-013/036/037/038/039/040/041 source. Integration into Proposal/GO/store is a separately reviewed P-V6-1B slice after the standalone v2 and migration-preview contract passes.

## 21. Regression matrix

- v1 canonical/package schema equality and existing v1 fixtures unchanged;
- v2 closed schema, deterministic serialization and tamper rejection;
- character multiplicity/order/duplicate/primary validation;
- Space/Composition zero-or-one validation;
- Start and End intentional differences accepted;
- unresolved v1 references cannot auto-apply;
- preview binds exact source checksum and becomes stale on change;
- migration output deterministic and never claims GO/provider/native authority;
- two-hour frame ranges use integer/end-exclusive semantics;
- full Product tests, compileall, JavaScript syntax and diff check;
- WSL2 and GitHub matrix before merge.

## 22. Design completion

All 21 mandatory design work packages and the 36 requested concern areas are covered by this design plus the current-main audit, imported UX contract and native acceptance plan. The remaining uncertainty is empirical interaction/native Evidence, intentionally deferred to P-V6-6 and not represented as PASS.
