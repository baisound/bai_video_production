# TASK-013 Future Slice — Scene-Compatible Reference / Shot Feasibility Gate Detailed Design Ver.1.0

- Date: `2026-08-12`
- Status: `DESIGN_REGISTERED / IMPLEMENTATION_NOT_AUTHORIZED`
- Knowledge input: `BVP-KNOWLEDGE-REFIMG-001`
- Future implementation owner: `TASK-013 — AI SE / BGM / Video Orchestration`
- Runtime provider/execution foundation: `TASK-004`
- Asset identity/checksum authority: `TASK-003`
- Optional creative/edit context input: `TASK-007`
- Timeline/Resolve mutation: outside this slice
- Product runtime dependency on BAI Development OS: `PROHIBITED`

## 1. Objective

AI image/video generation before provider execution must reject scene/reference combinations that are structurally contradictory.

The system shall not treat Character consistency + Room consistency as sufficient. A third condition is mandatory:

`SCENE_PHYSICAL_FEASIBILITY`

A provider request can become generation-ready only when the Scene's subject placement, camera, required visible elements and prohibited changes can coexist in a Scene-Compatible Room / Shot Reference.

## 2. Ownership

TASK-004 already provides local image/video runtime foundations, Character Identity, provider-neutral reference bundles and H3 production brief generation. It must not be reopened for ordinary creative orchestration expansion.

TASK-013 owns future admission/orchestration:

- TASK-004 executes admitted generation requests.
- TASK-013 decides whether Scene/reference intent is admissible and compiles a provider-neutral generation request.
- TASK-003 provides canonical Asset identity/checksums/rights.
- TASK-007 may provide content/edit context when selection depends on the Edit Plan.
- TASK-010 / TASK-026 remain Timeline execution/placement owners.

## 3. Non-Goals

This design does not:

- implement a 3D room reconstruction engine,
- claim that multiple 2D references establish exact geometry,
- make Midjourney a required provider,
- infer missing furniture geometry as fact,
- allow an AI vision model to silently override a failed structural/human gate,
- change TASK-004 historical completion,
- authorize TASK-013 implementation,
- mutate Resolve or media,
- bake editorial overlays into generated image assets.

## 4. Canonical Contracts

### 4.1 `SceneGenerationReferenceSpec`

```json
{
  "spec_version": "1.0.0",
  "scene_id": "P01",
  "continuity_type": "CUT",
  "character_identity_profile_id": "CHAR-...",
  "character_reference_asset_ids": ["ASSET-..."],
  "room_master_asset_id": "ASSET-...",
  "room_shot_reference_asset_id": "ASSET-...",
  "style_reference_asset_id": null,
  "required_visible": ["FACE", "NOTEBOOK", "MONITOR"],
  "subject_orientation": "THREE_QUARTER_FRONT_TO_CAMERA",
  "camera_position": {
    "semantic": "DESK_FRONT_LEFT",
    "azimuth_degrees": 35
  },
  "start_frame_source": "NEW",
  "previous_end_asset_id": null,
  "prohibited_changes": [
    "ADD_DESK",
    "MOVE_FURNITURE",
    "ROTATE_DESK",
    "MOVE_WINDOW",
    "MOVE_DOOR"
  ]
}
```

### 4.2 `ContinuityType`

- `CUT`
- `DIRECT_CONTINUATION`
- `MATCH_CUT`
- `GRAPHIC_TRANSITION`

### 4.3 `StartFrameSource`

- `NEW`
- `PREV_END`

Rules:

- `DIRECT_CONTINUATION` requires `PREV_END`.
- `PREV_END` requires a canonical previous End Asset.
- Previous End is reused by identity and checksum, not regenerated.
- Other continuity types may create a new Start subject to Gate PASS.

### 4.4 Reference Roles

Each reference binding has exactly one primary role:

- `CHARACTER_IDENTITY`
- `ROOM_MASTER`
- `SCENE_SHOT_COMPOSITION`
- `STYLE_TONE`
- `PREVIOUS_END_CONTINUITY`

A reference may not satisfy a different authority merely because a provider accepts it.

## 5. `ShotFeasibilityAssessment`

```json
{
  "assessment_version": "1.0.0",
  "scene_id": "P01",
  "status": "PASS",
  "checks": {
    "subject_position_exists": "PASS",
    "orientation_camera_compatible": "PASS",
    "required_visible_coexists": "PASS",
    "prohibited_change_not_required": "PASS",
    "shot_reference_matches_final_camera": "PASS",
    "reference_roles_valid": "PASS",
    "continuity_contract_valid": "PASS"
  },
  "decision_source": "HUMAN_REVIEWED_STRUCTURED_ASSERTION",
  "blocking_reasons": []
}
```

Allowed states:

- `PASS`
- `FAIL`
- `UNVERIFIED`

Overall:

- any `FAIL` -> `FAIL`
- no `FAIL` but any `UNVERIFIED` -> `REVIEW_REQUIRED`
- all required checks `PASS` -> `PASS`

Only overall `PASS` may become `GENERATION_READY`.

## 6. No Fake Automatic Geometry Proof

The source Knowledge requires physical feasibility but does not define a reliable automatic geometry evaluator.

Therefore the first Product implementation shall be fail-closed:

- structured metadata proves deterministic contract facts,
- human review confirms visual/physical feasibility,
- optional AI vision analysis may produce advisory findings,
- advisory AI output cannot turn `FAIL` or `UNVERIFIED` into `PASS` by itself.

A future automatic visual/geometric evaluator requires separate measured Evidence and authorization.

## 7. Gate Algorithm

### Stage A — Asset and rights admission

1. Resolve all Asset IDs through TASK-003.
2. Verify checksums.
3. Verify rights / Job boundary policy.
4. Reject missing or untrusted local paths before provider staging.

### Stage B — Continuity resolution

If `DIRECT_CONTINUATION`:

1. `start_frame_source` must be `PREV_END`.
2. previous End Asset must exist.
3. next Start binding must equal previous End Asset ID.
4. expected SHA-256 must match.
5. provider image generation for Start is skipped.

Any mismatch fails closed.

### Stage C — Reference role validation

1. Character identity reference exists where a character is required.
2. Scene Shot Reference exists for character-in-room generated shots.
3. Style Reference remains optional.
4. Room Overview alone is insufficient unless independently certified as the exact Scene Shot Reference.

### Stage D — Feasibility checks

Required:

1. `subject_position_exists`
2. `orientation_camera_compatible`
3. `required_visible_coexists`
4. `prohibited_change_not_required`
5. `shot_reference_matches_final_camera`

### Stage E — Generation readiness

Only `PASS` creates immutable/checksummed `GenerationReadySceneReference`.

## 8. Scene Asset Matrix

Minimum columns:

| Field | Purpose |
|---|---|
| `scene_id` | Scene identity |
| `continuity_type` | transition contract |
| `character_profile` | identity binding |
| `room_master` | overall spatial source |
| `shot_reference` | scene-compatible composition |
| `required_visible` | simultaneous visual requirements |
| `subject_orientation` | subject direction |
| `camera_position` | shot direction/height |
| `prohibited_changes` | negative physical contract |
| `start_source` | NEW / PREV_END |
| `start_asset` | approved Start |
| `end_asset` | approved End |
| `feasibility_status` | gate result |
| `generation_status` | lifecycle |
| `qa_status` | visual QA |

Lifecycle:

`DRAFT -> FEASIBILITY_REVIEW -> GENERATION_READY -> START_GENERATED -> START_APPROVED -> END_GENERATED -> END_APPROVED -> VIDEO_READY`

`DIRECT_CONTINUATION` may enter `START_APPROVED` by exact previous-End reuse after continuity verification.

## 9. Provider Compilation

Provider adapters receive an already admitted Scene contract.

Example mapping:

- Character identity -> provider Character/Omni/Reference mechanism
- Scene Shot Reference -> provider Image Prompt / image conditioning
- Style tone -> provider style reference only
- Start/End Assets -> first/last frame inputs where supported

Provider capability differences must not weaken Product Gate semantics. Unsupported role preservation means unsupported request, not silent approximation.

## 10. Start / End Rules

### Start

- New Start requires Gate PASS.
- Start is generated without design overlays.
- Start receives human/QA approval before End generation.

### End

- End is generated only after Start approval for the same shot.
- End binds approved Start and continuity requirements.

### Scene boundary

- `DIRECT_CONTINUATION`: exact previous End -> next Start reuse.
- Other continuity types: new Start permitted after a new feasibility assessment.

## 11. Overlay Separation

Generation payload must not include:

- Scene ID
- timecode
- QA status
- narration text
- subtitles
- explanatory callouts
- debug labels

These belong to EDIT / OVERLAY.

## 12. Evidence and Privacy

May store by default:

- Scene ID
- reference role
- Asset IDs/checksums
- gate check results
- provider/model/profile identifiers
- continuity type
- prohibited-change codes
- output Asset IDs/checksums
- human approval state

Do not store by default:

- raw prompt text
- transcript/subtitle bodies
- private media bytes
- secrets
- unrelated personal data

## 13. Error Taxonomy

- `SHOT_REF_MISSING`
- `SHOT_REF_NOT_SCENE_COMPATIBLE`
- `SUBJECT_POSITION_UNVERIFIED`
- `CAMERA_ORIENTATION_CONFLICT`
- `REQUIRED_VISIBLE_CONFLICT`
- `PROHIBITED_GEOMETRY_CHANGE_REQUIRED`
- `STYLE_REFERENCE_USED_AS_GEOMETRY_AUTHORITY`
- `DIRECT_CONTINUATION_PREV_END_MISSING`
- `DIRECT_CONTINUATION_ASSET_MISMATCH`
- `OVERLAY_CONTENT_IN_GENERATION_REQUEST`
- `REFERENCE_ROLE_CONFLICT`

## 14. Acceptance Tests

1. P01 conflict fixture fails when Room Overview cannot show face + notebook + monitor without layout change.
2. P01 compatible 30–45 degree Shot Reference passes structured/human-reviewed gate.
3. Missing subject position never auto-PASSes.
4. Style Reference alone cannot satisfy shot geometry.
5. A requirement needing a new desk fails.
6. DIRECT_CONTINUATION uses exact previous End Asset ID and hash.
7. DIRECT_CONTINUATION attempting new Start generation fails.
8. CUT may use new Start after a new assessment.
9. Overlay/debug text is rejected from generation-layer fields.
10. Provider mapping cannot silently collapse Character and Scene Shot roles.
11. Evidence contains no raw prompt body by default.
12. Same contract produces deterministic assessment identity/hash.

## 15. Future Implementation Slices

### TASK-013 Slice REF-A — Contract + Gate Core

- data contracts
- JSON Schema
- deterministic validators
- continuity resolver
- gate Evidence
- no provider calls

### TASK-013 Slice REF-B — Generation Request Compiler

- TASK-004 Character Identity / reference bundle integration
- provider-neutral -> provider-specific mapping
- fail-closed capability mismatch

### TASK-013 Slice REF-C — Scene Asset Matrix / Human Review UI

- Scene matrix
- visual reference preview
- Shot Feasibility review
- Start/End approval lifecycle
- exact previous-End reuse

### TASK-013 Slice REF-D — Optional Advisory Visual QA

- AI vision advisory analysis
- measured false-pass/false-fail Evidence
- never authority by default

## 16. Critic Design Findings

- Do not reopen TASK-004: accepted.
- Physical feasibility cannot be declared automatically without proof: accepted.
- Continuity must be Asset/bytes based, not perceptual similarity: accepted.
- Provider terminology must not become Product Core contract: accepted.
- Room Master and Scene Shot Reference remain distinct: accepted.

## 17. Judge Design Decision

`PASS FOR DOCUMENTATION / FUTURE IMPLEMENTATION RESERVATION`

This design may be registered now without changing runtime behavior or editing-first execution order.

Implementation remains unauthorized until TASK-013 is explicitly selected and its implementation slice passes the normal Builder/Critic/Judge gate.

## 18. Promotion Team Intake Addendum Ver.1.1

The 2026-08-12 Promotion Team production/audit handoff strengthens this future design without changing TASK ownership.

### 18.1 Required planning sequence

For character-in-space shots, the canonical planning order becomes:

`Scene Intent -> Visibility Contract -> Task Axis -> Depth Order -> Final Camera -> Empty Final Shot Reference -> Character Injection -> Identity/Geometry QA`

Camera is a consequence of Task Axis and Visibility Contract. The actor must not be rotated unnaturally merely to satisfy camera-facing preference.

### 18.2 Additional hard checks

`ShotFeasibilityAssessment` shall add or explicitly map:

- `task_axis_valid`
- `depth_order_valid`
- `occlusion_valid`
- `furniture_integrity_valid`
- `room_anchor_integrity_valid`
- `production_gear_absent`
- `character_identity_valid` after Character Injection

A new desk/table required only to make the shot possible is a structural failure, not a Prompt wording issue.

### 18.3 Two-stage generation

Stage A: generate and approve the person-less Final Shot Reference.

Stage B: inject the Character Identity into the approved shot reference without redesigning the room.

Stage C: run Identity / Geometry / Prop / Task Axis QA before promoting the result to canonical Start Frame.

### 18.4 Failure escalation

Repeated identical structural Failure Code two or more consecutive times must stop Prompt micro-edit retries.

The routing action becomes one of:

- `RETURN_TO_VISIBILITY_CONTRACT`
- `RETURN_TO_TASK_AXIS`
- `RETURN_TO_DEPTH_ORDER`
- `RETURN_TO_FINAL_CAMERA`
- `REBUILD_FINAL_SHOT_REFERENCE`

### 18.5 P01/P14 regression fixture

The Promotion evidence provides a concrete regression fixture:

`Camera -> Monitor foreground -> Desk/Notebook -> C01 -> S01 Background`

For that fixture, Monitor behind C01 is a hard FAIL even if aesthetic quality is high.

This fixture is a test example, not a universal depth order for unrelated Scenes.

### 18.6 Audit handoff

TASK-013 does not own the general audit system.

Generation results emit structured reference/gate/failure Evidence to TASK-038, where AI/Human review, alternate-use classification and regeneration decisions are managed.

TASK-040 owns Prompt Version / regeneration routing contracts.

TASK-037 owns Asset Slot / Candidate Version / Lock / Stale relationships.
