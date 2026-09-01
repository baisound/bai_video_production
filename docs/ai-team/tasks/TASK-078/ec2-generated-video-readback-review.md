# E-C2 — Generated Video Typed Media Read-back and Review

- Candidate Task identity: `TASK-080`
- Integration owner: `TASK-013` terminal read-back + `TASK-038` Human Review
- Canonical owners preserved: `TASK-013`, `TASK-003`, `TASK-027`, `TASK-037`,
  `TASK-038`, `TASK-036`
- DEV profile: `DEV-4`
- Dependency: merged E-C1 Scene epoch binding
- Parallel with: E-C4
- Effect authority in this design: `NONE`

## 1. Goal and non-duplication

Replace the current `output_ref + output_sha256 + media_kind`-only completion
proof for generated video with an exact typed media receipt stored inside the
same TASK-013 terminal execution file. Then carry that receipt through the
existing TASK-027 adoption, TASK-003 `GENERATED_VIDEO` Asset, TASK-038 Audit and
TASK-037 ACCEPT/LOCK lifecycle.

E-C2 does not introduce another media file, Asset registry, Candidate store,
Audit store or Human decision state machine.

## 2. Same-file terminal receipt ABI

`GeneratedVideoTerminalReceipt` is a required exact nested object in a TASK-013
`COMPLETED` event in `generation-executions.json`. No sidecar can substitute.

```text
receipt_version = 1.0.0
record_type = GeneratedVideoTerminalReceipt
task_owner = TASK-013
project_id
production_job_id
scene_id
scene_epoch                    explicit integer >= 0
scene_epoch_binding_sha256
queue_entry_id
queue_snapshot_sha256
execution_id
provider_operation_id
output_ref                     project-output:// logical ref
output_sha256
asset_type = GENERATED_VIDEO
media_kind = VIDEO
container                      closed safe token
video_codec                    closed safe token
pixel_format                   closed safe token
width                          1..32768
height                         1..32768
frame_rate_numerator           positive bounded integer
frame_rate_denominator         positive bounded integer; reduced rational
frame_count                    positive bounded integer
duration_numerator             reduced exact seconds numerator
duration_denominator           reduced exact seconds denominator
timing_mode = CFR
has_audio                      boolean
audio_codec                    exact safe token iff has_audio
audio_sample_rate_hz           positive iff has_audio
audio_channels                 positive iff has_audio
probe_policy_sha256
media_bytes_read = true
provider_replayed = false
candidate_created = false
timeline_mutation_started = false
receipt_sha256
```

Exact duration is `frame_count * frame_rate_denominator /
frame_rate_numerator`, reduced into the duration fields. VFR, zero-frame,
unreduced/non-positive rates, inconsistent duration, multiple video streams,
unsupported rotation/display geometry and ambiguous container/codec are not a
successful E-C2 terminal.

The TASK-013 execution port returns only private probe observations. TASK-013
validates output containment and byte hash, compiles the typed receipt and then
atomically appends one `COMPLETED` event containing it. Probe or validation
failure appends `FAILED_KNOWN` when no uncertain provider state exists. A crash
after provider dispatch but before terminal publication remains
`RECOVERY_REQUIRED`; recovery may read provider history/output and append one
terminal event but must never call execute again.

## 3. Adoption and Asset ABI

TASK-027 adoption accepts generated video only when the current terminal event
contains a byte-valid typed receipt and current E-C1 epoch. It does not perform
a re-hash/re-probe followed by an unlocked second path read. Under the Product
lock it streams the output once into a TASK-003-owned write-once adoption blob,
computes the hash while copying, closes/fsyncs it, then opens that exact blob
under a deny-write/immutable staging guard for probe and ingest. The blob
receipt binds terminal output hash, byte length, probe policy and staging blob
identity; it contains no browser-visible path.

The receipt is exact:

```text
receipt_version = 1.0.0
record_type = GeneratedVideoAdoptionBlobReceipt
task_owner = TASK-003
receipt_id
project_id/production_job_id/scene_id/scene_epoch
scene_epoch_binding_sha256
queue_entry_id/execution_id/terminal_receipt_sha256
terminal_output_sha256
terminal_media_facts_sha256
blob_logical_id/blob_byte_length/blob_sha256
probe_policy_sha256
guard_state = CLOSED_FSYNCED_DENY_WRITE
prepared_asset_store_snapshot_sha256
adoption_operation_id
state = READY_FOR_PREVALIDATED_INGEST
host_path_exposed = false
provider_replayed = false
asset_committed = false
receipt_sha256
```

`receipt_id` and `adoption_operation_id` are deterministic over the immutable
Project/Job/Scene/terminal/blob coordinates. It remains immutable READY
evidence. Success is represented separately by:

```text
receipt_version = 1.0.0
record_type = GeneratedVideoAdoptionCommitReceipt
task_owner = TASK-003
receipt_id
adoption_operation_id
parent_blob_receipt_id/sha256
project_id/production_job_id/scene_id/scene_epoch
scene_epoch_binding_sha256
terminal_receipt_sha256
asset_id/asset_sha256
pre_asset_store_snapshot_sha256
post_asset_store_snapshot_sha256
asset_store_revision
state = COMMITTED
committed_at
provider_replayed = false
candidate_created = false
receipt_sha256
```

The commit receipt ID is deterministic over the operation, parent, Asset and
post-store head. The Asset transaction appends it atomically with the exact
Asset row. A sidecar, caller-supplied blob identity, different store snapshot,
different bytes, missing parent, or same operation with a different Asset/head
cannot resume or commit the operation.

TASK-003 gains a narrow prevalidated-ingest transaction: it copies/streams from
that same guarded blob, recomputes hash and media facts, and commits the Asset
row only in the same transaction after expected terminal hash/media CAS passes.
Failure leaves canonical Asset mutation count zero. Recovery may reuse only the
same blob receipt and exact bytes; another file/ref requires a fresh adoption
operation. Orphan staging bytes are noncanonical and require bounded cleanup,
never automatic Asset registration.

The canonical TASK-003 Asset remains `AssetRecord` with
`asset_type=GENERATED_VIDEO`. Its `media_metadata` exact E-C2 profile contains:

```text
profile = TASK080_GENERATED_VIDEO_MEDIA_V1
terminal_receipt_sha256
scene_epoch
scene_epoch_binding_sha256
container/video_codec/pixel_format
width/height
frame_rate {numerator, denominator}
frame_count
duration {numerator, denominator}
has_audio/audio fields
```

Generation provenance adds `terminal_receipt_sha256` and the Scene epoch
coordinates. Rights remain conservative (`UNKNOWN`, Human rights review and
publication-not-authorized restrictions). Typed media PASS never promotes
rights or publication readiness.

`production_job_id` is the existing TASK-001/003 Product Job identity, not a
new E-C Job type. TASK-027 Queue admission reads it from the current Product
Project/Job binding, stores it in the exact Queue snapshot and carries the same
identity through TASK-013 terminal, TASK-003 Asset, Candidate and Timeline
lineage. Cross-Job substitution fails at every hop.

TASK-037 generated-video Candidate lineage stores the terminal receipt hash,
Scene epoch and Asset checksum as one exact optional generated-video binding.
The optional field is illegal for IMAGE and mandatory for E-C2
`GENERATED_VIDEO` Candidates.

## 4. Review ABI and Human authority

TASK-038 remains the Audit/Human-decision owner. Playback observation is a
separate exact Human operation, not a caller-supplied boolean. Preparation
binds Candidate/Asset/terminal receipt, playable byte hash, current Audit and
Production snapshots and a minimum complete playback range `[0,frame_count)`;
it also requires this trusted native-player receipt:

```text
receipt_version = 1.0.0
record_type = TrustedGeneratedVideoPlaybackReceipt
task_owner = TASK-038
receipt_id
project_id/production_job_id/scene_id/scene_epoch
scene_epoch_binding_sha256
player_session_id/trusted_player_port_id/trusted_player_port_version
candidate_id/asset_id/asset_sha256/terminal_receipt_sha256
decoded_media_sha256
decoded_frame_count
observed_contiguous_start_frame = 0
observed_contiguous_end_frame = frame_count
range_convention = HALF_OPEN
observation_mode = NATIVE_PLAYER_DECODED_FRAMES
started_at/completed_at
browser_claim_accepted = false
provider_timeline_export_effect_started = false
receipt_sha256
```

The TASK-038 trusted desktop player port issues this only after its private
native frame callbacks prove the complete contiguous decoded range for the
exact Asset bytes. The port is registered through the trusted launcher; the
WebView can request playback but cannot submit session IDs, frame ranges,
completion or receipt bodies. Preparation seals this receipt and apply re-reads
it from the TASK-038 store. The Human confirmation explicitly attests
`WATCHED_COMPLETE_RANGE`; the native receipt proves playback occurred, while
the Human attestation supplies the decision authority.

Apply consumes one bounded token, revalidates every coordinate and appends a
`GeneratedVideoPlaybackObservationReceipt` in the TASK-038 store:

```text
receipt_version = 1.0.0
record_type = GeneratedVideoPlaybackObservationReceipt
task_owner = TASK-038
receipt_id
project_id/production_job_id/scene_id/scene_epoch
scene_epoch_binding_sha256
candidate_id/asset_id/asset_sha256/terminal_receipt_sha256
trusted_player_receipt_id/sha256
decoded_media_sha256
playback_start_frame = 0
playback_end_frame = frame_count
playback_range_convention = HALF_OPEN
prepared_audit_snapshot_sha256
prepared_production_snapshot_sha256
human_actor_id
human_attestation = WATCHED_COMPLETE_RANGE
observed_at
observation_state = COMPLETE
provider_or_timeline_effect_started = false
receipt_sha256
```

AI audits cannot create this type and the parser rejects the type in an AI
writer route. A `GeneratedVideoHumanReviewReceipt` is then created only by the
existing TASK-038 Human decision prepare/confirm/apply transaction. It binds
the exact playback receipt ID/SHA, Human Audit ID/SHA, decision ID/body SHA,
prepared snapshots and terminal receipt SHA. The Audit row's
`GeneratedVideoReviewBinding` v1.0 is included only for a generated-video
Candidate and binds those receipts:

```text
receipt_version = 1.0.0
record_type = GeneratedVideoHumanReviewReceipt
task_owner = TASK-038
receipt_id
project_id/production_job_id/scene_id/scene_epoch
scene_epoch_binding_sha256
candidate_id/asset_id/asset_sha256/terminal_receipt_sha256
playback_observation_receipt_id/sha256
audit_id/audit_sha256
human_decision_id/human_decision_body_sha256
decision = ACCEPT | REJECT | NEEDS_REGENERATION
prepared_audit_snapshot_sha256
prepared_production_snapshot_sha256
human_actor_id/decided_at
review_state = APPLIED
provider_timeline_export_publication_effect_started = false
receipt_sha256
```

The receipt ID is deterministic over the decision ID/body and all bound
snapshots. Only `decision=ACCEPT` is eligible for TASK-037; replay with another
body/snapshot, AI-writer construction, or cross-Candidate receipt is rejected.

```text
task_owner = TASK-038
project_id/scene_id/scene_epoch
candidate_id/asset_id/asset_sha256
terminal_receipt_sha256
audit_id
technical_dimension_present = true
contract_dimension_present = true
continuity_dimension_present = true
playback_observation_receipt_id/sha256
human_review_receipt_id/sha256 nullable until Human decision
prepared_audit_snapshot_sha256
prepared_production_snapshot_sha256
review_binding_sha256
```

Automated inspection may create a TASK-038 Audit with TECHNICAL/CONTRACT/
CONTINUITY findings, but it cannot create or populate a playback/Human-review
receipt. ACCEPT requires one current `GeneratedVideoHumanReviewReceipt` bound
to the same terminal and playback receipts, zero unresolved critical findings
and the existing explicit Human decision. A boolean alone is never authority.
LOCK remains the separate TASK-037 one-shot Human operation.

For a generated-video Candidate, TASK-037 apply-lock also appends one exact
`GeneratedVideoLockReceipt` in the same Production snapshot transaction. It
binds Project/Scene/epoch, Slot/Candidate/Asset, terminal media receipt,
playback/Human review receipt and pre/post Production snapshot hashes. Its
effect flags state that it authorizes no Timeline, Resolve, Export or
publication operation. E-C3 requires this receipt ID/SHA rather than trusting
`candidate_state=LOCKED` alone.

```text
receipt_version = 1.0.0
record_type = GeneratedVideoLockReceipt
task_owner = TASK-037
receipt_id
project_id/production_job_id/scene_id/scene_epoch
scene_epoch_binding_sha256
slot_id/candidate_id/asset_id/asset_sha256
terminal_receipt_sha256
playback_observation_receipt_id/sha256
human_review_receipt_id/sha256
human_decision_body_sha256
prepared_production_snapshot_sha256
committed_production_snapshot_sha256
lock_operation_id
lock_state = LOCKED
locked_by/locked_at
timeline_resolve_export_publication_authorized = false
receipt_sha256
```

Receipt and operation IDs are deterministic over the bound ACCEPT decision and
pre-commit Production head. The receipt is appended atomically with that exact
post-commit snapshot. A replay returns the existing receipt only when every
byte matches; changed snapshot, Slot, Candidate, Asset or review is a conflict.

Review UI displays duration, rational fps, resolution, container, codec, audio
presence, checksum abbreviation and current Scene epoch alongside the playable
contained Asset. It never exposes `output_ref` or a host path to JavaScript.

## 5. UI transitions

| State | Screen/status | Only next action |
|---|---|---|
| Job `DISPATCHING` | AI Video: `生成中` | wait/reconcile; no duplicate run |
| completed bytes, typed receipt absent | `Media read-back未完了` | owner recovery |
| typed terminal current | `監査候補へ登録可能` | TASK-027 adoption confirmation |
| Asset/Candidate `READY_FOR_AUDIT` | Asset Review: `動画確認待ち` | Human playback/audit |
| Audit critical/epoch stale | `修正または再生成が必要` | Reject/Needs regeneration |
| Human ACCEPT | `WORLD LOCK待ち` | TASK-037 lock confirmation |
| LOCKED current | `Timeline配置準備完了` | hand off to E-C3 |

## 6. Restart and failure

- Same-file terminal event is the only terminal source of truth. Asset metadata
  or UI caches cannot repair a missing terminal receipt.
- Reopening the Project reparses event -> terminal receipt -> Asset -> Candidate
  -> Audit/decision/LOCK. Any mismatch is `DATA_INTEGRITY_BLOCKED`.
- Pending execution/adoption/review/lock tokens disappear on restart without an
  effect.
- If Asset registration succeeded but Candidate registration did not, existing
  TASK-027 exact-suffix recovery may continue only after revalidating terminal
  receipt, bytes, media facts and current epoch.
- If a Scene epoch advances after completion, bytes remain evidence/history;
  adoption, ACCEPT, LOCK and later placement are blocked.
- Review transaction ambiguity uses TASK-038 recovery; no Human decision is
  inferred from an Audit row or playback event.

## 7. Negative matrix

| Case | Result | Forbidden promotion |
|---|---|---|
| output hash drift | terminal/adoption integrity reject | Asset/Candidate |
| VFR/zero frame/bad rational | `FAILED_KNOWN` or recovery blocker | COMPLETED |
| width/height/container/codec mismatch on re-probe | adoption reject | Asset |
| typed receipt in sidecar only | reject | terminal completion |
| cross execution/Queue/Scene/epoch | reject | adoption/review |
| typed receipt current but rights UNKNOWN | review allowed; publication blocked | rights PASS |
| AI audit marks playback observed | schema reject | Human ACCEPT |
| forged playback boolean without receipt | ignored/reject | Human ACCEPT |
| browser/player receipt body or session/range supplied by caller | reject | Human ACCEPT |
| trusted player receipt wrong bytes/noncontiguous/partial | apply reject | Human ACCEPT |
| blob receipt supplied as sidecar/forged/cross-snapshot | reject | Asset mutation 0 |
| blob operation replay with different bytes/terminal | conflict | Asset mutation 0 |
| playback receipt for partial/wrong bytes | apply reject | Human ACCEPT |
| output replaced between blob copy/probe/ingest | guarded blob/CAS reject | Asset mutation 0 |
| Human decision without exact bound audit | TASK-038 reject | ACCEPT |
| Human review receipt cross-Candidate/snapshot or AI-written | reject | ACCEPT |
| ACCEPT without current epoch/terminal hash | TASK-037 reject | LOCK |
| lock receipt cross-Slot/review/snapshot or replay drift | reject | placement |
| old IMAGE Candidate with generated-video binding | schema reject | placement |
| cap+1/duplicate/unknown field/version | fail closed | all |

## 8. Future implementation Allowed Files

- `src/ai_video_production/creative_generation_execution_application.py`
- `src/ai_video_production/media_probe.py`, only for typed probe result fields
- `src/ai_video_production/generation_output_adoption_application.py`
- `src/ai_video_production/ingest.py`
- `src/ai_video_production/assets.py`
- `src/ai_video_production/production_control.py`
- `src/ai_video_production/production_control_store.py`
- `src/ai_video_production/production_control_application.py`, only to append
  the exact generated-video lock receipt in the existing apply-lock transaction
- `src/ai_video_production/candidate_audit.py`
- `src/ai_video_production/candidate_audit_store.py`, only for canonical
  playback/Human-review receipt persistence and parsing
- `src/ai_video_production/audit_application.py`
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/task036_shell_v611.py`
- `src/ai_video_production/task036_product_ports.py`, only for the trusted
  TASK-038 player port boundary
- `src/ai_video_production/task036_trusted_launcher.py`, only for private player
  port registration
- new `schemas/generated-video-terminal-receipt.schema.json`
- new `src/ai_video_production/schema_resources/generated-video-terminal-receipt.schema.json`
- new `schemas/generated-video-review-receipts.schema.json`
- new `src/ai_video_production/schema_resources/generated-video-review-receipts.schema.json`
- `schemas/asset-record.schema.json`
- `src/ai_video_production/schema_resources/asset-record.schema.json`
- `schemas/generation-output-adoption.schema.json`
- `src/ai_video_production/schema_resources/generation-output-adoption.schema.json`
- `docs/ai-team/tasks/TASK-037/schemas/production-control-asset-registry.schema.json`
- `docs/ai-team/tasks/TASK-038/schemas/audit-workspace.schema.json`
- `tests/test_task013_creative_generation_execution_application.py`
- `tests/test_task003_asset_ingest.py`
- `tests/test_assets_and_store.py`
- `tests/test_task027_generation_output_adoption_application.py`
- `tests/test_task037_production_control.py`
- `tests/test_task037_production_control_store.py`
- `tests/test_task037_production_control_application.py`
- `tests/test_task038_candidate_audit.py`
- `tests/test_task038_candidate_audit_store.py`
- `tests/test_task038_audit_application.py`
- `tests/test_task036_visual_generation_handoff.py`
- `tests/test_task036_shell_ui.py`
- `tests/test_task036_v611_visual_contract.py`
- `tests/test_task036_product_ports.py`
- `tests/test_task036_trusted_launcher.py`
- new `docs/ai-team/tasks/TASK-080/task.md`
- new `docs/ai-team/tasks/TASK-080/ec2-implementation-evidence.md`
- `docs/ai-team/current-state.md`
- `docs/ai-team/task-index.md`

Provider adapter behavior, credentials, TASK-077, IMAGE placement, Timeline,
ProjectSave, Final Gate, Export, CHANGELOG, Release and Deploy files are
forbidden unless a new design review explicitly reallocates them.

## 9. Prohibited effects

The design and its contract-only implementation phase authorize no Provider or
paid call, new native generation, Timeline/Resolve write, rights approval,
publication, Export execution, Release, Deploy or Activation. A later
Owner-authorized runtime validation may read one already generated local file;
that authority is not granted by TASK-078.

## 10. Handoff

E-C2 hands E-C3 a current LOCKED `GENERATED_VIDEO` Candidate with exact Asset,
terminal media receipt, Human review binding and Scene epoch coordinates. It
hands E-C5 read-only stage projections. Handoff is ready only when same-file
terminal/re-probe/restart/Audit/LOCK negatives pass, existing IMAGE and generic
Audit compatibility remain green and residual C/H is `0 / 0`.
