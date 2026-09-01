# E-C5 — Packaged Vertical Aggregate / EXE F0-F10

- Candidate Task identity: `TASK-083`
- Integration owner: `TASK-036` Unified Desktop Shell
- Canonical owners: read-only composition of TASK-028/032..034, TASK-027,
  TASK-013, TASK-003/037/038, TASK-043/044, E-C4 owner
  readers and TASK-011 Export QA
- DEV profile: `DEV-4`
- Dependency: merged E-C3 (therefore E-C1, E-C2 and E-C4)
- Effect authority in this design: `NONE`

## 1. Goal and aggregate boundary

Present one restart-safe packaged EXE progression from model selection to
Export result read-back without adding a second orchestrator or durable
aggregate store. `Task036EcVerticalProjection` reads exact canonical snapshots,
computes F0-F10 and returns one deterministic next action. It writes nothing.

All mutation commands remain the owning workspace's prepare/confirm/apply
operations. The aggregate can navigate and refresh only.

## 2. Aggregate receipt ABI

`EcVerticalProjection` is a checksum-closed ephemeral projection:

```text
projection_version = 1.0.0
record_type = EcVerticalProjection
task_owner = TASK-036
project_id/project_manifest_sha256
source_snapshot_sha256s          exact closed map below
scene_epoch/scene_epoch_binding_sha256 nullable before F3
timeline_sha256                  nullable before F7
final_approval_receipt_sha256    nullable before F9
export_job_id/result_ref         nullable before F9/F10
stages                           exact ordered 11 rows
workflow_blocking_stage          lowest noncurrent prerequisite or null
active_recovery_stage            already-started effect recovery stage or null
aggregate_state = BLOCKED | READY | IN_PROGRESS | RECOVERY_REQUIRED |
                  COMPLETE | STALE | UNKNOWN | SOURCE_UNAVAILABLE
next_action
next_action_owner = TASK-043 | TASK-028 | TASK-027 | TASK-013 |
                    TASK-003 | TASK-037 | TASK-038 | TASK-044 | TASK-041 |
                    TASK-016 | TASK-020 | TASK-036 | NONE
recovery_source = PROJECT_SAVE | VIDEO_EXECUTION | VIDEO_ADOPTION |
                  AUDIT_DECISION | TIMELINE_PLACEMENT | OWNER_GATE |
                  EXPORT_DISPATCH | EXPORT_QA | null
provider_execution_authorized = false
timeline_mutation_authorized = false
final_approval_authorized = false
export_dispatch_authorized = false
release_deploy_activation_authorized = false
projection_sha256
```

Each stage row is exact:

```text
stage_id F0..F10
owner
state = BLOCKED | READY | IN_PROGRESS | RECOVERY_REQUIRED | COMPLETE |
        STALE | UNKNOWN | SOURCE_UNAVAILABLE
source_receipt_sha256s           exact stage-specific closed map; values nullable
blocker_codes sorted unique capped 32
navigation_target
effect_started boolean, true only when canonical owner evidence proves it
```

The top-level source map has exactly these keys: `project`, `central_models`,
`planning`, `scene_epoch`, `generation_queue`, `generation_execution`,
`asset_adoption`, `audit_production`, `timeline_project_save`,
`owner_gate_bundle`, `final_approval_export_job`, and `export_result`. Each is
the canonical hash of the corresponding stage source map, not a substitute for
its members.

Stage source keys are exact:

| Stage | Required source receipt keys |
|---|---|
| F0 | `project_manifest`, `project_save_integrity` |
| F1 | `central_model_settings`, `planning_route`, `video_route` |
| F2 | `approved_plan`, `proposal`, `blueprint` |
| F3 | `task027_scene_finalization`, `scene_epoch_binding` |
| F4 | `generation_queue` |
| F5 | `execution_terminal`, `generated_video_media` |
| F6 | `asset`, `output_adoption`, `audit`, `playback_observation`, `human_review`, `production_lock` |
| F7 | `project_save_terminal`, `timeline`, `placement_currentness` |
| F8 | `audio_reader`, `edit_reader`, `privacy_reader`, `resource_reader`, `rights_reader` |
| F9 | `final_readiness`, `final_approval_v2`, `export_job` |
| F10 | `dispatch_admission`, `export_job`, `render_result`, `render_qa`, `artifact_readback` |

A missing member is explicit null plus a blocker until its stage exists.
Unknown/extra keys or a stage aggregate hash not matching the full member map
reject the projection. This prevents a single primary receipt from hiding the
multi-owner F6/F8/F10 evidence.

The projection hash excludes only UI-local rendering details. It never includes
host paths, media bytes, Prompt bodies, credentials, private Gate Evidence or
runner/adapters.

## 3. Exact F0-F10 definitions

| Stage | Owner/source | COMPLETE predicate | Next when not complete |
|---|---|---|---|
| F0 Project current | TASK-043 | Project Manifest/current children integrity PASS; no ProjectSave recovery | open/recover Project |
| F1 Central model | TASK-028/032..034 | exact current compatible Planning + Video route/model selections; credentials are configuration only | Connection Settings/model selection |
| F2 Planning | TASK-027 | current Human GO-approved Plan/Proposal/Blueprint | Planning workspace |
| F3 Scene epoch | TASK-027 + E-C1 | current TASK-027 Scene finalization and epoch binding | TASK-027 Scene Design/finalization |
| F4 AI Video Job | TASK-027 | current epoch-bound Queue entry exists in admitted state | AI Video Queue |
| F5 Generated media read-back | TASK-013 + E-C2 | same-file COMPLETED terminal receipt and exact current bytes/media facts | execute/reconcile/media recovery |
| F6 Review and LOCK | TASK-003/027/038/037 | GENERATED_VIDEO Asset, current Human playback/Audit ACCEPT and exact LOCK | adoption/Asset Review/WORLD LOCK |
| F7 Timeline placement | TASK-043/044 + E-C3 | current v1.2 generated-video placement persisted and ProjectSave/currentness PASS | Edit placement/recovery |
| F8 Owner Final Gates | TASK-041/016/020/003/027/044 | exact five owner receipts PASS/current for current Timeline/epoch | owning Gate workspace |
| F9 Final Approval and Queue | TASK-036 + TASK-044 | current typed Human Final Approval and exactly one scoped durable Export Job | Final Review/Queue add |
| F10 Export result read-back | TASK-044 + TASK-011 | same Job SUCCEEDED, exact result identity, Render QA PASS and durable artifact read-back current | dispatch/reconcile/result review |

F1 does not imply Provider execution authority. F8 does not imply Final
Approval. F9 Queue existence does not imply dispatch. F10 does not imply
publication, Release, Deploy or Production Activation.

## 4. Aggregate state and deterministic next action

The action precedence is total and uses two distinct lanes:

| Priority | Condition | Selected action rule |
|---:|---|---|
| 1 | an already-admitted external effect is `RECOVERY_REQUIRED/UNKNOWN` at F5 or F10 | reconcile the lowest such stage read-only; never replay |
| 2 | ProjectSave/placement transaction recovery exists at F0/F7 | exact owning recovery action |
| 3 | no active recovery | action for the lowest F0-F10 stage not COMPLETE/current |
| 4 | all stages COMPLETE/current | `NONE` |

`workflow_blocking_stage` always records the lowest noncurrent prerequisite,
even while `active_recovery_stage` temporarily determines the one primary
action. Reconciliation cannot promote a later stage past the earlier blocker.
For example F3 STALE + F10 UNKNOWN selects `RECONCILE_EXPORT`, retains F3 as the
workflow blocker, and after reconciliation selects `FINALIZE_SCENE_STRUCTURE`.
A later COMPLETE stage never hides an earlier STALE/UNKNOWN stage.

Within the selected stage, the first matching row below is the only primary
action. Every predicate is evaluated from the exact stage source map; an
unlisted state/value combination is `UNKNOWN` with blocker
`UNRECOGNIZED_CANONICAL_COMBINATION` and no mutating action.

| Stage, ordered predicate | Stage state | Blocker code | Primary action | Owner |
|---|---|---|---|---|
| F0 ProjectSave/current-integrity recovery exists | RECOVERY_REQUIRED | `PROJECT_SAVE_RECOVERY` | RECOVER_PROJECT_SAVE | TASK-043 |
| F0 Project absent | READY | `PROJECT_MISSING` | OPEN_PROJECT | TASK-043 |
| F0 integrity current | COMPLETE | — | continue | NONE |
| F1 compatible Planning route or Video route missing/stale | READY | `CENTRAL_MODEL_SELECTION_REQUIRED` | SELECT_CENTRAL_MODEL | TASK-028 |
| F1 both exact selections current | COMPLETE | — | continue | NONE |
| F2 Proposal/Blueprint absent, non-GO or stale | READY | `PLAN_APPROVAL_REQUIRED` | APPROVE_PLAN | TASK-027 |
| F2 current Human GO-approved set | COMPLETE | — | continue | NONE |
| F3 TASK-027 finalization or current binding absent/stale | READY or STALE | `SCENE_FINALIZATION_REQUIRED` | FINALIZE_SCENE_STRUCTURE | TASK-027 |
| F3 TASK-027 finalization and binding current | COMPLETE | — | continue | NONE |
| F4 no current epoch-bound Queue row | READY | `VIDEO_JOB_REQUIRED` | CREATE_AI_VIDEO_JOB | TASK-027 |
| F4 current admitted Queue row | COMPLETE | — | continue | NONE |
| F5 no execution admission/dispatch exists | READY | `VIDEO_EXECUTION_CONFIRMATION_REQUIRED` | CONFIRM_VIDEO_EXECUTION | TASK-013 |
| F5 effect-started state is DISPATCHING/RECOVERY_REQUIRED/UNKNOWN | RECOVERY_REQUIRED | `VIDEO_EXECUTION_RECONCILIATION` | RECONCILE_VIDEO_EXECUTION | TASK-013 |
| F5 terminal exists but typed media/current bytes not read back | READY | `GENERATED_MEDIA_READBACK_REQUIRED` | READ_BACK_GENERATED_MEDIA | TASK-013 |
| F5 current typed terminal/read-back exists | COMPLETE | — | continue | NONE |
| F6 Asset/output adoption absent | READY | `GENERATED_VIDEO_ADOPTION_REQUIRED` | ADOPT_GENERATED_VIDEO | TASK-027 |
| F6 playback/Human review absent or not ACCEPT/current | READY | `GENERATED_VIDEO_REVIEW_REQUIRED` | REVIEW_GENERATED_VIDEO | TASK-038 |
| F6 ACCEPT current but exact lock absent | READY | `GENERATED_VIDEO_LOCK_REQUIRED` | LOCK_GENERATED_VIDEO | TASK-037 |
| F6 Asset/review/lock all current | COMPLETE | — | continue | NONE |
| F7 participant/result currentness recovery exists | RECOVERY_REQUIRED | `TIMELINE_PLACEMENT_RECOVERY` | RECOVER_TIMELINE_PLACEMENT | TASK-044 |
| F7 placement absent/stale | READY or STALE | `GENERATED_VIDEO_PLACEMENT_REQUIRED` | PLACE_GENERATED_VIDEO | TASK-036 |
| F7 placement and ProjectSave integrity current | COMPLETE | — | continue | NONE |
| F8 Edit source/currentness recovery exists | RECOVERY_REQUIRED | `EDIT_PERSISTENCE_RECOVERY` | RECOVER_EDIT_PERSISTENCE | TASK-044 |
| F8 Audio not CURRENT_PASS | BLOCKED | `AUDIO_GATE_REQUIRED` | RESOLVE_AUDIO_GATE | TASK-041 |
| F8 Privacy not CURRENT_PASS | BLOCKED | `PRIVACY_GATE_REQUIRED` | RESOLVE_PRIVACY_GATE | TASK-016 |
| F8 Resource not CURRENT_PASS | BLOCKED | `RESOURCE_GATE_REQUIRED` | RESOLVE_RESOURCE_GATE | TASK-020 |
| F8 Rights not CURRENT_PASS | BLOCKED | `RIGHTS_GATE_REQUIRED` | RESOLVE_RIGHTS_GATE | TASK-003 |
| F8 Edit not CURRENT_PASS and no active recovery journal | BLOCKED | `EDIT_GATE_REQUIRED` | RESOLVE_EDIT_GATE | TASK-044 |
| F8 all five readers CURRENT_PASS | COMPLETE | — | continue | NONE |
| F9 approval v2 absent/stale | READY or STALE | `FINAL_APPROVAL_REQUIRED` | FINAL_APPROVE | TASK-036 |
| F9 approval current, operation-indexed Export Job absent | READY | `EXPORT_ENQUEUE_REQUIRED` | ENQUEUE_EXPORT | TASK-044 |
| F9 exact approval and unique Job exist | COMPLETE | — | continue | NONE |
| F10 Job QUEUED/READY and no dispatch admission | READY | `EXPORT_DISPATCH_CONFIRMATION_REQUIRED` | CONFIRM_EXPORT_DISPATCH | TASK-044 |
| F10 DISPATCHING/UNKNOWN/RECOVERY_REQUIRED | RECOVERY_REQUIRED | `EXPORT_RECONCILIATION_REQUIRED` | RECONCILE_EXPORT | TASK-044 |
| F10 RENDER_SUCCEEDED_QA_PENDING | RECOVERY_REQUIRED | `EXPORT_QA_READBACK_REQUIRED` | RECONCILE_EXPORT | TASK-044 |
| F10 SUCCEEDED but QA/read-back missing/mismatched | UNKNOWN | `EXPORT_RESULT_INTEGRITY_REQUIRED` | RECONCILE_EXPORT | TASK-044 |
| F10 same-Job SUCCEEDED + QA PASS + current read-back | COMPLETE | — | NONE | NONE |

For F8, the table's owner order is exact even if several blockers exist. For
all other rows, any `SOURCE_UNAVAILABLE` remains visible and routes to the same
read-only owner workspace/reconciliation action only when that action cannot
start an effect; otherwise primary action is `WAIT_FOR_SOURCE` with the
unavailable stage owner. `WAIT_FOR_SOURCE` performs no call or mutation.

Closed next actions:

```text
OPEN_PROJECT
WAIT_FOR_SOURCE
RECOVER_PROJECT_SAVE
SELECT_CENTRAL_MODEL
APPROVE_PLAN
FINALIZE_SCENE_STRUCTURE
CREATE_AI_VIDEO_JOB
CONFIRM_VIDEO_EXECUTION
RECONCILE_VIDEO_EXECUTION
READ_BACK_GENERATED_MEDIA
ADOPT_GENERATED_VIDEO
REVIEW_GENERATED_VIDEO
LOCK_GENERATED_VIDEO
PLACE_GENERATED_VIDEO
RECOVER_TIMELINE_PLACEMENT
RESOLVE_AUDIO_GATE
RESOLVE_PRIVACY_GATE
RESOLVE_RESOURCE_GATE
RESOLVE_RIGHTS_GATE
RESOLVE_EDIT_GATE
RECOVER_EDIT_PERSISTENCE
FINAL_APPROVE
ENQUEUE_EXPORT
CONFIRM_EXPORT_DISPATCH
RECONCILE_EXPORT
NONE
```

`OPEN_EXPORT_RESULT` is a non-primary navigation affordance on a COMPLETE F10
row; opening or not opening a view is UI-local and cannot change projection
state.

`NONE` remains legal only when every stage is COMPLETE/current;
`WAIT_FOR_SOURCE` is the distinct blocked no-effect action.

If more than one E-C4 Gate blocks, next action follows the closed owner order
Audio, Privacy, Resource, Rights, Edit while the UI lists every blocker.
`NONE` is legal only when F0-F10 are all COMPLETE/current.

## 5. Export Queue and result read-back

E-C5 reuses P-UX-2D5/E1 and TASK-044 durable Export Job ownership.

- Final Approval prepare/apply re-reads all current sources and owner receipts.
- Queue add is a distinct explicit Human confirmation. Its immutable
  `export_operation_id` is `sha256(canonical-json([project_id, timeline_id,
  timeline_revision, timeline_sha256, scene_epoch,
  scene_epoch_binding_sha256, final_approval_receipt_sha256,
  export_profile_sha256, logical_output_identity]))`. TASK-044 enforces a
  unique CAS index from that ID to one durable Job. Restart or a repeated apply
  with the identical operation ID returns the same Job without a new enqueue;
  an ID mapped to different bytes, or the same approval mapped to a different
  operation ID, is an integrity conflict and creates no Job.
- Dispatch prepare/apply is another explicit confirmation. Private launcher
  bindings own output destination and dispatcher; browser cannot inject them.
- Dispatch apply uses the E-C4 `FinalGateDispatchAdmissionGate`; the same Job
  CAS persists the exact `Task044ExportDispatchAdmissionReceipt` and
  `DISPATCHING` before renderer/native effect.
- Renderer success first advances that same Job to
  `RENDER_SUCCEEDED_QA_PENDING` with the immutable logical result identity,
  output SHA and renderer result receipt. Restart performs only idempotent,
  read-only probe/QA against those exact result bytes. It never invokes the
  renderer again. A result-ref/hash mismatch is `RECOVERY_REQUIRED`, not a new
  render.
- Only a final same-Job CAS may advance to `SUCCEEDED`; it binds the exact
  TASK-011 Render QA PASS receipt and the Job-hash-independent artifact
  read-back payload hash. Failure or
  crash before that CAS leaves `RENDER_SUCCEEDED_QA_PENDING` and resumes QA.
- The read-back projection is derived from canonical Job + TASK-011 records; it
  is not a second artifact store. It exposes no host path.
- An interrupted dispatch becomes UNKNOWN/reconciliation-required on restart
  and is never auto-rendered.

This is a narrow EXPORT-only TASK-043 durable Job ABI v1.2 continuation of the
E-C4 v1.1 dispatch admission fields. It has
`job_record_version=1.2.0` and adds these exact canonical Job fields:

```text
logical_output_identity
renderer_result_ref                 private logical ref
renderer_result_receipt_sha256
result_output_sha256
render_qa_receipt_sha256
artifact_readback_payload             full nested ExportArtifactReadbackPayload
```

Variant selection and state grammar are exact:

| Structural variant | Admitted states | Admission | v1.2 result fields | legacy `result_ref` |
|---|---|---|---|---|
| legacy v1.0 exact field set, no `job_record_version` | all ten legacy states under the E-C4 migration rules | field absent | fields absent | existing legacy rule |
| v1.1 exact field set, `job_record_version=1.1.0` | DISPATCHING, RUNNING, UNKNOWN, HUMAN_REQUIRED, FAILED, CANCELLED | full nested receipt required | fields absent | null |
| v1.2 exact field set, `job_record_version=1.2.0` | RENDER_SUCCEEDED_QA_PENDING | full nested receipt required | first four nonnull; QA/payload null | null |
| v1.2 exact field set, `job_record_version=1.2.0` | SUCCEEDED | full nested receipt required | all six nonnull | nonnull and exactly equal to `renderer_result_ref` |

The parser selects v1.0 only by its exact historical field set, and v1.1/v1.2
only by both discriminator and exact mutually exclusive field set. Missing,
extra, overlapping or unknown variants and every state/variant combination not
listed above fail closed. `source_job_version` in the projection is this exact
structural version (`1.2.0`), not `state_version` or store revision. A v1.1
UNKNOWN may advance to v1.2 QA_PENDING only after read-only reconciliation
proves the exact same admitted renderer result; post-effect HUMAN_REQUIRED
cannot resume PREFLIGHT or create a new dispatch. QA failure remains v1.2
QA_PENDING with its owner QA Evidence and never reruns the renderer.

Every transition is one `DurableProductJobService.transition` revision CAS.
Existing v1.0 non-EXPORT and v1.1 pre-result Job bytes/behavior remain
unchanged; migration is explicit parse-by-version, never silent
reserialization.

At QA_PENDING, existing core `result_ref` is null. At SUCCEEDED it must equal
`renderer_result_ref`; the payload and projection copy logical result identity,
ref and output facts only from that same Job renderer-result binding. A caller
cannot supply a second result coordinate.

`ExportArtifactReadbackPayload` is compiled from the exact renderer result and
same-result media probe before the SUCCEEDED CAS. The full object is nested in
that canonical Job record. It does not include Job revision/record SHA or
projection SHA:

```text
payload_version = 1.0.0
record_type = ExportArtifactReadbackPayload
task_owner = TASK-044
export_operation_id/export_job_id/export_profile_sha256
logical_output_identity/renderer_result_receipt_sha256/output_sha256
container/video_codec/pixel_format/width/height
frame_rate_numerator/frame_rate_denominator/frame_count
duration_numerator/duration_denominator
has_audio/audio_codec/audio_sample_rate_hz/audio_channels
render_qa_receipt_sha256
host_path_exposed = false
publication_release_deploy_activation_started = false
payload_sha256
```

The same CAS validates TASK-011 PASS, validates every payload media fact against
the renderer result/probe, and stores the full payload object. Thus restart can
reparse `frame_count`, rate, duration, geometry, codecs and audio facts without
reprobing or relying on TASK-011 fields that do not carry them. After the
SUCCEEDED CAS, the read-only projection binds the final Job record SHA plus the
nested payload SHA and computes its own projection SHA. The projection SHA is
never written back to the Job, and the payload does not contain the Job SHA, so
no hash cycle exists.

`ExportArtifactReadbackProjection` is exact and checksum closed:

```text
projection_version = 1.0.0
record_type = ExportArtifactReadbackProjection
task_owner = TASK-044
project_id/project_manifest_sha256
timeline_id/timeline_revision/timeline_sha256
scene_epoch/scene_epoch_binding_sha256
final_approval_receipt_sha256
export_operation_id
export_job_id/export_job_revision
export_job_state = SUCCEEDED
dispatch_admission_receipt_id/sha256
export_profile_sha256
logical_output_identity
result_ref                         private logical ref; never a host path
renderer_result_receipt_sha256
output_sha256
container/video_codec/pixel_format
width/height
frame_rate_numerator/frame_rate_denominator
frame_count
duration_numerator/duration_denominator
has_audio
audio_codec/audio_sample_rate_hz/audio_channels  null iff no audio
render_qa_receipt_sha256
render_qa_result = PASS
artifact_readback_payload_sha256
source_job_record_sha256
source_job_version
host_path_exposed = false
publication_started = false
release_deploy_activation_started = false
current_state = CURRENT | STALE | SOURCE_UNAVAILABLE | INTEGRITY_ERROR
projection_sha256
```

The duration and frame-rate rationals are reduced and must satisfy
`duration_numerator / duration_denominator = reduce(frame_count *
frame_rate_denominator / frame_rate_numerator)`; bounds and media token policy
equal the E-C2 typed-video profile. The projection reparses the exact Job result and
TASK-011 receipt, requires identical Job/result/output SHA, requires the E-C4
dispatch-admission receipt and `SUCCEEDED` terminal revision, and computes
currentness against the current Project/Timeline/epoch/approval/profile. A
different Job, output, QA receipt, version, or result identity is an integrity
error. Missing QA/read-back is not success.

Actual Resolve/native execution, if selected, remains a separately authorized
Owner/native gate. Synthetic/package tests cannot satisfy that real-runtime
gate.

## 6. EXE UI

The unified `BAI Video Production.exe` Home/Production status surface shows an
accessible F0-F10 stepper plus one primary next-action button. Each row shows
owner, current state, safe receipt abbreviation, blockers and navigation.

Required behaviors:

- keyboard access and visible focus for every row/action;
- Narrator/UIA name includes stage, state, owner and blocker count;
- no color-only state meaning;
- 100/125/150/200% DPI and supported viewport reflow;
- progress survives restart by canonical reread, not local storage;
- SOURCE_UNAVAILABLE/error/recovery remains visible after navigation/reopen;
- one event listener per action after merged Shell composition;
- separate confirmations clearly distinguish Provider execution, Timeline
  placement, Final Approval, Queue add and Export dispatch;
- result view offers open-in-app/readback only, not publish/release/deploy.

## 7. Restart and failure matrix

The packaged acceptance matrix is:

| Restart point | Required read-back | Forbidden behavior |
|---|---|---|
| F0 before Project open | empty/project picker | fabricate Project |
| F1 after model save | exact current selection | treat credential as execution GO |
| F2 after Plan GO | exact Plan/Proposal/Blueprint | auto-finalize Scene |
| F3 after Scene completion | current TASK-027 finalization/epoch | use old epoch |
| F4 after Queue admission | same durable Queue row | duplicate Job |
| F5 during DISPATCHING | recovery/UNKNOWN | replay Provider |
| F5 after terminal | same-file typed media receipt | trust sidecar/cache |
| F6 after Human ACCEPT/LOCK | exact Audit/Production history | infer decision from playback |
| F7 during ProjectSave | exact COMPLETE/ROLLBACK choice | auto-select recovery |
| F8 after owner PASS then revoke | STALE/REVOKED blocker | cached PASS |
| F9 after approval/queue | current/stale approval + same Job | duplicate enqueue |
| F10 during Export DISPATCHING | UNKNOWN reconciliation | auto-render |
| F10 after renderer success before QA | same Job `RENDER_SUCCEEDED_QA_PENDING` | render again |
| F10 after success | same Job/result/QA/artifact read-back | infer publication |

## 8. Global negative matrix

| Case | Aggregate result | Effect |
|---|---|---:|
| F3 STALE while a started F10 effect is UNKNOWN | reconcile F10, retain F3 blocker, then select F3 | 0 replay/new workflow effects |
| source snapshot cross Project/Timeline | projection reject | 0 |
| typed media missing | F5 blocked | 0 |
| IMAGE placement mistaken for generated video | F7 blocked | 0 |
| synthetic/cached owner Gate PASS | F8 blocked | 0 |
| Final Approval stale after owner revoke | F9 stale | 0 dispatch |
| multiple Jobs for one approval | integrity/recovery blocker | 0 new |
| same operation ID with different canonical bytes | integrity conflict | 0 new |
| same approval with a different operation ID | integrity conflict | 0 new |
| Job SUCCEEDED without QA/readback | F10 UNKNOWN/BLOCKED | no completion claim |
| renderer success followed by restart | resume same-result QA | 0 renders |
| read-back cross-Job/result/output/QA | integrity error | 0 |
| non-EXPORT/v1.0 Job gains result/QA fields | compatibility failure; PR blocked | 0 |
| QA-pending/SUCCEEDED Job field nullability mismatch | parser/CAS reject | 0 replay |
| SUCCEEDED `result_ref != renderer_result_ref` | parser/CAS/read-back reject | 0 |
| unknown/overlapping Job version or state combination | fail closed | 0 |
| projection SHA stored in/fed back into Job | schema reject; hash-cycle prevention | 0 |
| SUCCEEDED Job stores payload SHA without full payload body | parser/CAS reject | 0 completion claim |
| nested payload media facts drift from renderer result/probe | CAS/read-back reject | 0 |
| result host path reaches WebView | security failure; PR blocked | 0 |
| unknown stage/state/action/extra field/cap+1 | fail closed | 0 |
| UI says complete without canonical receipt | visual contract failure | 0 |

## 9. Future implementation Allowed Files

- new `src/ai_video_production/ec_vertical_projection.py`
- `src/ai_video_production/task036_workflow_runtime.py`
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/task036_shell_v611.py`
- `src/ai_video_production/task036_trusted_launcher.py`
- `src/ai_video_production/final_review_readiness.py`
- `src/ai_video_production/final_review_application.py`
- `src/ai_video_production/final_review_export_application.py`
- `src/ai_video_production/export_queue_application.py` only for canonical
  read-back projection/query gaps
- `src/ai_video_production/export_queue.py` only if a body-free result readback
  coordinate is missing from the typed contract
- `src/ai_video_production/durable_product_job.py`, only for EXPORT v1.2
  QA-pending/result/readback fields and atomic transition CAS
- `schemas/durable-product-job.schema.json`
- `src/ai_video_production/schema_resources/durable-product-job.schema.json`
- new `schemas/ec-vertical-projection.schema.json`
- new `src/ai_video_production/schema_resources/ec-vertical-projection.schema.json`
- new `schemas/export-artifact-readback.schema.json`
- new `src/ai_video_production/schema_resources/export-artifact-readback.schema.json`
- new `tests/test_task083_ec_vertical_projection.py`
- `tests/test_task036_workflow_runtime.py`
- `tests/test_task036_shell_ui.py`
- `tests/test_task036_v611_visual_contract.py`
- `tests/test_task036_v611_interaction_contract.py`
- `tests/test_task036_trusted_launcher.py`
- `tests/test_task036_packaged_entry.py`
- `tests/test_task036_packaging.py`
- `tests/test_task036_final_review_export.py`
- `tests/test_task036_pux2e_export_dispatch.py`
- `tests/test_task044_export_queue.py`
- `tests/test_task043_durable_product_job.py`
- `tests/test_task043_project_save_recovery.py`
- new `tests/test_task083_windows_f0_f10_acceptance.py`, using only packaged
  fakes in the contract implementation PR
- new `docs/ai-team/tasks/TASK-083/task.md`
- new `docs/ai-team/tasks/TASK-083/ec5-implementation-evidence.md`
- `docs/ai-team/current-state.md`
- `docs/ai-team/task-index.md`

No owner record writer may be added to TASK-036. Provider adapter, Asset/Audit/
Timeline mutation semantics, owner Gate decision logic, Resolve implementation,
CHANGELOG, version, Release and Deploy files are forbidden unless a fresh design
review reallocates them.

## 10. Prohibited effects

TASK-078/E-C5 authorizes no Provider/paid/native call, Timeline/Resolve write,
Final Approval, Export Queue mutation/dispatch, publication, Release, Deploy or
Activation. Future TASK-083 may implement read-only aggregate/Shell wiring; any
real action continues to require its existing owner command and Human/native
gate.

## 11. Handoff and completion

E-C5 is ready for implementation handoff only when F0-F10 ownership/source
predicates are exact, every next action routes to an existing owner, all restart
points fail without replay, owner receipt revocation stales Final Approval,
successful Export requires same-Job QA/artifact read-back, EXE accessibility and
DPI contracts are complete, and residual C/H is `0 / 0`.

Packaged closure later requires clean-profile Windows F0-F10 restart evidence,
viewport/DPI screenshots, keyboard/Narrator/UIA/focus/error persistence and one
separately Owner-authorized real-media/native Export read-back when the selected
route requires it. Contract or synthetic PASS alone cannot claim that closure.
