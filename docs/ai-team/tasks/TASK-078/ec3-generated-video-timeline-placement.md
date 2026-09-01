# E-C3 — GENERATED_VIDEO-only Timeline Placement

- Candidate Task identity: `TASK-082`
- Integration owner: `TASK-044`
- Canonical owners preserved: `TASK-003`, `TASK-037`, `TASK-038`, `TASK-043`,
  `TASK-044`; `TASK-036` is Shell composition only
- DEV profile: `DEV-4`
- Dependencies: merged E-C2 and E-C4
- Effect authority in this design: `NONE`

## 1. Goal and strict type boundary

Place one already current, Human-reviewed and LOCKED
`AssetType.GENERATED_VIDEO` Candidate into the canonical TASK-044 Timeline,
with exact duration/rate/track/range and ProjectSave recovery semantics.

The existing `task036_visual_asset_placement.py` P-UX-2H IMAGE eligibility and
`PLACED_LOCKED_ASSET` behavior remain exact and unchanged. E-C3 adds a separate
`task036_generated_video_placement.py` facade and accepts no IMAGE, VIDEO source
Asset or audio type. Shared TASK-044 grammar is amended only through a new
versioned generated-video binding.

## 2. Eligibility receipt ABI

`GeneratedVideoPlacementEligibilityReceipt` is a read-only TASK-044 admission
receipt compiled from exact owner records:

```text
receipt_version = 1.0.0
record_type = GeneratedVideoPlacementEligibilityReceipt
task_owner = TASK-044
receipt_id
project_id/project_manifest_sha256
production_snapshot_sha256
scene_id/scene_epoch/scene_epoch_binding_sha256
slot_id/slot_kind = VIDEO | VFX
candidate_id/candidate_state = LOCKED
generated_video_lock_receipt_id/sha256
asset_id/asset_sha256/asset_type = GENERATED_VIDEO
terminal_media_receipt_sha256
human_review_binding_sha256
target_timeline_id/target_timeline_sha256/target_timeline_revision
timeline_rate_numerator/timeline_rate_denominator
source_frame_count
source_rate_numerator/source_rate_denominator
mapped_duration_frames
target_track_id/target_track_role/target_track_media_kind
operation_kind = INSERT | REPLACE
target_clip_id                  null iff INSERT
before_clip_sha256              null iff INSERT
before_source_binding_sha256    null allowed only for legacy REPLACE source
insertion_policy = FAIL_ON_OVERLAP_NO_RIPPLE
target_start_frame/target_end_frame
source_in_frame = 0
source_out_frame = source_frame_count
range_convention = HALF_OPEN
owner_reader_bundle_available = true
publication_authorized = false
external_mutation_authorized = false
receipt_sha256
```

`receipt_id` is deterministic over the complete admission coordinates and
prepared Timeline/Production heads. It is read-only Evidence, not a Timeline
command token; prepare/apply separately bind its ID/SHA and revalidate all
sources.

E-C4 reader availability is checked because the Owner directed E-C3 dependency
requires the canonical reader composition to exist before placement. E-C3 does
not require the pre-placement Timeline's owner Gate receipts to PASS: placement
changes the Timeline hash and E-C4 must evaluate the newly persisted Timeline
afterward. Reader availability is not placement authority and no owner receipt
hash is persisted into the Timeline source binding.

### Rate and range rules

`mapped_duration_frames` is valid only when:

```text
source_frame_count * timeline_rate_numerator * source_rate_denominator
--------------------------------------------------------------------
source_rate_numerator * timeline_rate_denominator
```

is a positive integer. The initial E-C3 unit performs no retime, frame blending,
speed change, trim, padding or rounding. A non-integral mapping is
`RATE_CONFORM_REQUIRED` and effect zero.

- Every source and Timeline range is half-open: `[in_frame,out_frame)` and
  `[start_frame,end_frame)`. Insert starts at the explicit Human-selected frame and ends exactly
  at `start + mapped_duration_frames`.
- Replace requires exactly one selected visual clip, preserves its clip ID and
  track, and requires its existing range length to equal
  `mapped_duration_frames`. Preparation seals the exact target clip and current
  before clip/source-binding hashes.
- Insert and replace are `FAIL_ON_OVERLAP_NO_RIPPLE`; they never move another
  clip, extend the Timeline or silently overwrite an intersecting clip.
- The range must be positive and contained by the current Timeline duration.
- `SlotKind.VIDEO` targets a VIDEO-role/VIDEO-kind track.
- `SlotKind.VFX` targets an OVERLAY-role/VIDEO-kind track.
- Audio embedded in the source remains metadata only; E-C3 creates no audio
  track/clip and TASK-041 retains Audio ownership.

## 3. TASK-044 history ABI v1.2

Timeline edit history v1.2 adds generated-video source bindings while retaining
the v1.0 prefix and v1.1 IMAGE behavior byte-for-byte.

`GeneratedVideoTimelineSourceBinding` contains:

```text
binding_version = 1.0.0
media_binding_kind = GENERATED_VIDEO
project_id/production_snapshot_sha256
scene_id/scene_epoch/scene_epoch_binding_sha256
slot_id/candidate_id/asset_id/asset_sha256/production_job_id
generation_execution_id/queue_entry_id/terminal_media_receipt_sha256
human_review_binding_sha256
generated_video_lock_receipt_sha256
source_frame_count/source_rate rational
source_in_frame/source_out_frame
mapped_duration_frames/timeline_rate rational
publication_authorized = false
binding_sha256
```

The projected `InteractiveTimelineClip` uses
`state=PLACED_LOCKED_GENERATED_VIDEO`, `source_owner=TASK-003`, source ref Asset
ID/SHA and the Human Candidate ID. The binding, not the generic clip, owns
source range/rate facts.

The document/store envelope version is monotonic `1.0 -> 1.1 -> 1.2`. Inside a
v1.2 envelope, existing v1.0 legacy command variants and v1.1 IMAGE command
variants remain legal with their exact original row bytes and hashes; command
variant numbers are not a chronological downgrade rule. Only the envelope may
not downgrade after v1.2. New generated-video INSERT/REMOVE/REPLACE variants
carry exact before/after generated-video binding pairs; undo swaps them and redo
reuses them after fresh eligibility validation. Compatibility fixtures must
cover v1.0 rows + v1.1 IMAGE rows + v1.2 generated-video row + later unchanged
v1.1 IMAGE command bytes inside the v1.2 envelope.

## 4. ProjectSave transaction and recovery

E-C3 uses `ProductProjectSaveCoordinator` with a distinct participant identity
`TASK082_GENERATED_VIDEO_TIMELINE_PLACEMENT_V1`. It creates no second Timeline
or Project history.

Lock/linearization order is:

```text
E-C4 FinalGateDispatchAdmissionGate
  -> Project Manifest lock and E-C3 commit guard
  -> TASK-037 Production snapshot lock
  -> re-read exact Candidate/Slot/Asset/epoch/media/review binding
  -> verify E-C4 owner-reader composition availability (no owner decision/read)
  -> stage TASK-044 v1.2 child and participant recovery receipt
  -> TASK-043 Project Manifest commit
  -> TASK-044 history participant reconcile
  -> terminal ProjectSave journal
  -> Edit OwnerGateInvalidationJournal terminal INVALIDATION_COMMITTED
```

E-C3 is a TASK-044 Timeline upstream mutator and therefore participates in the
E-C4 Edit row. Under the outer admission Gate it appends the Edit
`OwnerGateInvalidationJournal` PREPARED before staging; its upstream operation
identity is the ProjectSave transaction ID. ROLLBACK with unchanged canonical
heads terminalizes ABORTED_NO_UPSTREAM_WRITE. A committed Timeline/Manifest is
not current until both ProjectSave and Gate invalidation journals are terminal.
The admission Gate is released only after that terminal state, so Export
dispatch cannot observe the new Timeline with the old Edit PASS.

No provider or owner-reader callback may execute while these locks are held.
The composition availability check is a pre-bound local capability identity,
not a call into an owner store. If it is unavailable, apply fails before any
recovery file is created.

The transaction ID includes the participant binding SHA. Every Timeline,
Final-Review, owner-Gate and E-C5 reader must first call
`ProductProjectSaveCoordinator.require_current_integrity`, then require the
matching participant plan/result receipt and terminal `COMMITTED` journal for
the current child/Manifest coordinate. The E-C3 placement-currentness ABI adds
`project_save_transaction_id`, `participant_binding_sha256`,
`participant_result_sha256` and `project_save_state=COMMITTED`. A Manifest that
points at the target child while reconciliation/journal termination is pending
is `RECOVERY_REQUIRED`, never current.

Interruption before
Manifest commit permits exact ROLLBACK; after Manifest commit only exact
COMPLETE is offered. Generic TASK-043 recovery without the matching participant
fails closed. A crash cannot leave a committed Timeline without the matching
history/result receipt, and two instances cannot overwrite or remove each
other's recovery files.

## 5. Human operation and UI

Public bridge methods are separate from P-UX-2H:

- `generated_video_placement_snapshot`
- `generated_video_placement_prepare_insert`
- `generated_video_placement_prepare_replace`
- `generated_video_placement_apply`
- `generated_video_placement_cancel`
- `generated_video_placement_recovery_status`
- `generated_video_placement_recover`

The Assets/Review page shows `動画をTimelineへ配置` only for an eligible LOCKED
GENERATED_VIDEO row. The dialog shows logical Scene/epoch/Candidate/Asset,
duration, source/timeline rate, track and exact source/target ranges. It exposes
no host path or media bytes. Apply refreshes canonical Assets, Review, Edit,
Final Review and E-C5 projections.

## 6. Restart and stale behavior

- Pending confirmations vanish on restart and produce no edit.
- A committed v1.2 revision and binding are reconstructed from TASK-044 history;
  no current Asset/Scene row is used to recreate historical binding bytes.
- Restart with a participant journal exposes only exact COMPLETE/ROLLBACK per
  commit state; no automatic choice or placement replay.
- Later Scene epoch, Candidate replacement, Asset/media receipt drift, review
  invalidation never rewrites history. Currentness projection marks the placed
  clip STALE and Final Review blocks. Owner Gates are evaluated for the new
  Timeline only after the placement commits; their later revocation stales
  Final Approval, not the historical placement.
- Undo removal requires exact Timeline CAS but no fresh placement authority.
  Redo insertion/replacement requires full fresh placement eligibility and the
  E-C4 owner-reader composition to remain available. Gate PASS is re-evaluated
  afterward for the resulting Timeline.

## 7. Negative matrix

| Case | Result | Timeline revision |
|---|---|---:|
| IMAGE/VIDEO/AUDIO Asset supplied | type reject; P-UX-2H unchanged | 0 |
| Candidate not LOCKED/current | eligibility reject | 0 |
| missing Human playback/review binding | eligibility reject | 0 |
| generated-video lock receipt wrong Slot/review/snapshot | eligibility reject | 0 |
| old Scene epoch | STALE blocker | 0 |
| non-integral rational rate mapping | `RATE_CONFORM_REQUIRED` | 0 |
| wrong VIDEO/VFX track role/kind | track reject | 0 |
| insert range outside Timeline | range reject | 0 |
| overlap would move/overwrite another clip | no-ripple collision reject | 0 |
| replace duration differs | exact-range reject | 0 |
| replace target/before clip or binding drift | token consumed; conflict | 0 |
| E-C4 owner-reader composition unavailable | admission reject | 0 |
| prepare/apply drift | token consumed; conflict | 0 |
| ProjectSave failure before Manifest | recovery ROLLBACK only | 0 committed |
| crash after Edit invalidation PREPARED before Timeline write | ABORTED_NO_UPSTREAM_WRITE recovery | 0 committed |
| failure after Manifest | recovery COMPLETE only | not exposed current until complete |
| wrong participant/tampered receipt | recovery reject | unchanged |
| redo after Asset/epoch stale | redo reject | 0 new |
| v1.0/v1.1 bytes reserialized | compatibility failure | PR blocked |
| Manifest target visible before participant COMMITTED | every reader returns RECOVERY_REQUIRED | 0 downstream |

## 8. Future implementation Allowed Files

- new `src/ai_video_production/task036_generated_video_placement.py`
- `src/ai_video_production/interactive_timeline.py`
- `src/ai_video_production/interactive_timeline_edit.py`
- `src/ai_video_production/interactive_timeline_store.py`
- `src/ai_video_production/interactive_timeline_application.py`
- `src/ai_video_production/project_save.py`
- `src/ai_video_production/final_review_readiness.py` only for stale-placement
  blocker composition
- `src/ai_video_production/task044_nle_shell.py`
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/task036_shell_v611.py`
- `src/ai_video_production/task036_trusted_launcher.py`
- new `schemas/generated-video-timeline-placement.schema.json`
- new `src/ai_video_production/schema_resources/generated-video-timeline-placement.schema.json`
- `schemas/project-command-history.schema.json`
- `src/ai_video_production/schema_resources/project-command-history.schema.json`
- `src/ai_video_production/schema_resources/project-save-journal.schema.json`
- new `tests/test_task082_generated_video_placement.py`
- `tests/test_task044_interactive_timeline.py`
- `tests/test_task044_timeline_edit_history.py`
- `tests/test_task044_nle_shell_ui.py`
- `tests/test_task043_project_save_recovery.py`
- `tests/test_task036_final_review_readiness.py`
- `tests/test_task036_shell_ui.py`
- `tests/test_task036_v611_visual_contract.py`
- `tests/test_task036_v611_interaction_contract.py`
- `tests/test_task036_trusted_launcher.py`
- new `docs/ai-team/tasks/TASK-082/task.md`
- new `docs/ai-team/tasks/TASK-082/ec3-implementation-evidence.md`
- `docs/ai-team/current-state.md`
- `docs/ai-team/task-index.md`

`task036_visual_asset_placement.py` is read-only compatibility evidence and is
not an Allowed File. Provider, Asset ingest, Audit decision, owner Gate writer,
Export, Resolve, audio, CHANGELOG, Release and Deploy files are forbidden.

## 9. Prohibited effects

TASK-078/E-C3 design grants no Timeline write. A future TASK-082 implementation
may implement Product-local Timeline/ProjectSave mutation only after separate
authority and review. Provider/paid/native generation, Resolve mutation, audio
placement, Final Approval, Export enqueue/dispatch, publication, Release,
Deploy and Activation remain prohibited.

## 10. Handoff

E-C3 hands E-C4/E-C5 a restart-readable v1.2 Timeline/Project Manifest
coordinate, generated-video source binding and placement-currentness hash so
the owner readers can issue receipts against the resulting Timeline. Handoff is ready
only when IMAGE v1.1 bytes/behavior are unchanged, all rate/range/track/
ProjectSave/restart/stale negatives pass, residual C/H is `0 / 0` and no
Provider/Resolve/Export effect occurred.
