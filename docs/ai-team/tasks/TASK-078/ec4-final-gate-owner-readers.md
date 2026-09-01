# E-C4 — Canonical Final Gate Owner Readers

- Candidate Task identity: `TASK-081`
- Receipt owners: `TASK-041` Audio, `TASK-016` Privacy, `TASK-020` Resource,
  `TASK-003` Rights/License, existing `TASK-044` Edit Persistence
- Lineage supplier only: `TASK-027`; consumer only: `TASK-036`
- DEV profile: `DEV-4`
- Design dependency: E-C1; parallel implementation with E-C2
- Runtime order: E-C3 commits Timeline -> E-C4 evaluates -> E-C5 approval
- Effect authority in this design: `NONE`

## 1. Goal and current gap

The current TASK-036 v1 Gate wrapper is a contract fixture that synthetic code
can construct; it is not packaged canonical authority. E-C4 gives every owner a
canonical source application/store and a deterministic read-only Final Gate
receipt. TASK-036 only reparses five owner reader results and records their
hashes in an explicit Human Final Approval.

The derived Final Gate receipt is not another append-only decision store. It is
re-derived from canonical owner source records on every read, so a later owner
successor/invalidation changes currentness without rewriting history.

## 2. Common owner receipt and reader-result ABI

Every derived owner receipt has this exact envelope:

```text
receipt_version = 2.0.0
record_type                    exact owner-specific value
task_owner                     exact single canonical owner
receipt_id
gate_id = AUDIO_COMPLETION | EDIT_PERSISTENCE | PRIVACY | RESOURCE | RIGHTS_LICENSE
project_id
timeline_id/timeline_revision/timeline_sha256
scene_epoch                    explicit integer >= 0
scene_epoch_binding_sha256
source_coordinates             exact owner-specific closed object
owner_store_snapshot_sha256
state_at_evaluation = PASS | FAIL | UNKNOWN | STALE | REVOKED
evaluated_at                   selected source time, not reader wall clock
authority_effect_created = false
publication_started = false
export_dispatch_authorized = false
receipt_sha256
```

`receipt_id` is deterministic over `task_owner`, `gate_id`, full requested
scope and `owner_store_snapshot_sha256`; identical canonical bytes reproduce
the same ID, while an ID/body collision is an integrity error.

Immutable receipts never self-assert perpetual currentness. Current selection
is separated into an owner-authored `OwnerFinalGateReaderResult`:

```text
reader_result_version = 1.0.0
record_type = OwnerFinalGateReaderResult
task_owner/gate_id
requested project/timeline/revision/hash/scene epoch coordinates
selected_receipt               full receipt or null for MISSING/unavailable/error
selected_receipt_sha256         same nullability as selected_receipt
selected_source_head_sha256     null for MISSING/unavailable/error
owner_store_snapshot_sha256     nullable only when store absent/unavailable
reader_state = CURRENT_PASS | CURRENT_BLOCKED | MISSING | SOURCE_UNAVAILABLE |
               INTEGRITY_ERROR
current_valid                  true iff CURRENT_PASS
current_invalidation_epoch     0 if current; positive after stale/revoked head; nullable as below
read_effect_created = false
reader_result_sha256
```

Nullability and values are total:

| Reader condition | `selected_receipt` / SHA / head | store snapshot | invalidation epoch | reader state |
|---|---|---|---:|---|
| store exists, exact current PASS | nonnull | nonnull | 0 | CURRENT_PASS |
| store exists, current FAIL/UNKNOWN/STALE/REVOKED | nonnull | nonnull | source epoch, 0 allowed only for FAIL/UNKNOWN without invalidation | CURRENT_BLOCKED |
| store exists but is valid and empty/no scoped row | all null | canonical empty-store SHA | 0 | MISSING |
| store absent or read unavailable | all null | null | null | SOURCE_UNAVAILABLE |
| malformed/fork/gap/ambiguous latest | all null | null if not safely computable, otherwise snapshot SHA | null | INTEGRITY_ERROR |

`current_invalidation_epoch` is therefore nullable only for unavailable or
integrity-error reads. `evaluated_at` in a derived owner receipt is the maximum
canonical source-record time among the exact selected source set, with ties
broken by canonical record SHA; it is absent because there is no receipt for
MISSING/unavailable/error states. Reader wall-clock time never enters a hash.

The reader validates source parent/revision continuity, fork/gap/multiple
latest, checksum, boundedness and exact scope. Historical PASS remains immutable
evidence, but a successor/invalidation yields a noncurrent reader result.
MISSING is typed absence, never default PASS.

## 3. Canonical owner source applications

Source applications use exact append-only records, canonical JSON, bounded
files, CAS, atomic replace, symlink/size rejection and Project-local locking.
They expose snapshot/read/prepare/apply/recover only; they do not perform media,
detector, collector, redaction, reservation, dispatch or publication effects.

### 3.1 Exact owner matrix

| Gate | `record_type` / `task_owner` | Exact `source_coordinates` keys | Cap and PASS derivation |
|---|---|---|---|
| Audio | `Task041FinalAudioGateReceipt` / `TASK-041` | `audio_source_truth_sha256`, `role_policy_sha256`, `canonical_completion_sha256`, `ledger_head_sha256`, `workspace_snapshot_sha256` | roles 6/items 1,024; canonical completion PASS/CURRENT and every required role/item source revalidated |
| Edit | `Task044FinalEditGateReceipt` / `TASK-044` | `project_manifest_sha256`, `timeline_sha256`, `edit_snapshot_sha256`, `history_head_sha256`, `project_save_terminal_receipt_sha256` | revisions 4,096; current integrity and exact COMMITTED ProjectSave result |
| Privacy | `Task016FinalPrivacyGateReceipt` / `TASK-016` | `policy_sha256`, `input_binding_sha256`, `evaluation_sha256`, `human_review_sha256`, nullable `redaction_plan_sha256`, `publication_gate_sha256`, `invalidation_set_sha256` | claims 512/invalidations 256; complete CURRENT Evidence, exact Human review, no invalidation, READY_FOR_EXTERNAL_HUMAN_GATE |
| Resource | `Task020FinalResourceGateReceipt` / `TASK-020` | `policy_sha256`, `observation_sha256`, `admission_decision_sha256`, `operation_gate_sha256` | facts 128/incidents 256; current ADMITTED and operation Gate ready for external Human review |
| Rights | `Task003FinalRightsLicenseGateReceipt` / `TASK-003` | `timeline_source_set_sha256`, `asset_registry_snapshot_sha256`, `rights_policy_sha256`, `rights_decision_set_sha256`, `task027_generation_lineage_set_sha256` | active sources/decisions 2,048; every Asset has current publication-compatible Human rights decision and no blocking restriction |

Unknown/extra keys, wrong nullable shape, unsorted source sets, cap+1 and owner/
type mismatch reject. The store snapshot hash covers the whole source collection
used for derivation.

### 3.2 Audio source application — TASK-041

Current Audio Completion R0/R1A/R1B evidence is diagnostic and cannot mint
canonical PASS/current/latest. E-C4 therefore includes prerequisite subunit
`TASK-081-A`: `Task041AudioCompletionGateApplication` revalidates the existing
immutable ledger, upstream owner records and source origin, then appends a
canonical `AudioCompletionSourceDecision` under TASK-041. It never promotes a
diagnostic candidate alone.

Prepare/apply freezes exact ledger/source heads and CAS. No new Human decision
is inferred: every required Human decision must already exist in the bound
TASK-041/026/014/035 records. Missing authority yields UNKNOWN/MISSING.
Invalidation appends through TASK-041 and advances reader invalidation epoch.

The prerequisite durable source record is exact:

```text
source_version = 1.0.0
record_type = AudioCompletionSourceDecision
task_owner = TASK-041
source_decision_id
project_id/timeline_id/timeline_revision/timeline_sha256
scene_epoch/scene_epoch_binding_sha256
audio_source_truth_sha256/role_policy_sha256/canonical_completion_sha256
ledger_head_sha256/workspace_snapshot_sha256
upstream_owner_record_sha256s       exact closed sorted map
decision = PASS | FAIL | UNKNOWN | REVOKED
parent_source_decision_sha256       null only for root
source_revision
prepared_store_snapshot_sha256
human_authority_inferred = false
effect_started = false
decided_at
source_decision_sha256
```

ID/revision/parent are CAS-bound. Only the canonical application may append;
diagnostic files, sidecars, changed upstream heads, a missing predecessor or
same ID with different bytes are rejected.

### 3.3 Privacy and Resource source applications

`Task016PrivacyGateApplication` stores only exact TASK-016 policy/input/
evaluation/Human-review/redaction/publication/invalidation records. It cannot
run detection or redaction.

`Task020ResourceGateApplication` stores only exact TASK-020 policy/observation/
decision/operation-gate/watermark/incident records for logical scope
`FINAL_REVIEW_EXPORT_READINESS`. It cannot collect facts, reserve resources or
authorize dispatch. Final Review PASS is readiness only; E-C5 requires a fresh
dispatch admission.

Both publish metadata through prepare/apply CAS and recovery. No source record
is accepted from WebView; trusted owner composition supplies typed records.

### 3.4 Rights source application — TASK-003 only

TASK-003 is the sole writer/store/revision/invalidation owner for
`RightsLicenseDecision`. TASK-027 supplies immutable generation provenance and
Scene-epoch lineage only and cannot mint/revise a Rights decision.

Human decision uses prepare -> explicit confirmation -> apply. The token seals
Project/Timeline source set, every Asset ID/SHA, policy, current rights fields/
restrictions, TASK-027 lineage, intended decision, actor and store CAS. Apply
consumes the token before revalidation. Revocation is another explicit TASK-003
append. No operation rewrites `AssetRecord`, clears restrictions or authorizes
publication. Generated Assets default UNKNOWN and cannot PASS without this
current decision.

```text
decision_version = 1.0.0
record_type = RightsLicenseDecision
task_owner = TASK-003
decision_id
project_id/timeline_id/timeline_revision/timeline_sha256
scene_epoch/scene_epoch_binding_sha256
timeline_source_set_sha256
asset_registry_snapshot_sha256
asset_identity_sha256s             sorted, capped 2,048
rights_policy_sha256
task027_generation_lineage_set_sha256
decision = PUBLICATION_COMPATIBLE | RESTRICTED | REJECTED | REVOKED
restriction_codes                  sorted closed set, empty only when compatible
parent_decision_sha256             null only at revision 1
decision_revision
prepared_store_snapshot_sha256
decided_by/decided_at
provider_timeline_export_publication_effect_started = false
decision_sha256
```

The decision ID identifies one logical Project/Timeline/source-set chain;
revision and parent are monotonic CAS-bound. Same revision/ID with different
bytes, a missing parent, cross-Asset/lineage substitution, AI-authored actor or
caller-cleared restrictions is rejected.

### 3.5 Edit source — TASK-044

TASK-044 projects its typed edit-persistence receipt plus E-C3 ProjectSave
participant/result/currentness into the v2 owner receipt. TASK-036 does not mint
the E-C Edit receipt through the old wrapper helper.

## 4. Cross-owner dispatch admission gate

Reader consistency at UI time cannot linearize revocation with dispatch.
TASK-044 owns `FinalGateDispatchAdmissionGate` only as a per-Project
linearization protocol; it owns no Gate decision. Every owner source append/
invalidation and TASK-044 dispatch admission participates.

```text
FinalGateDispatchAdmissionGate
  -> canonical owner locks in the exact order below
  -> TASK-044 durable Job lock/CAS
```

This is a Project-local OS/interprocess lock, not an in-process mutex. Every
mutator of a canonical head used by a Gate reader must acquire it *before* its
existing canonical lock; acquiring the admission Gate after an inner lock is
forbidden. Dispatch acquires every row in order. An ordinary owner mutation
acquires the admission Gate and only its row's locks, still in listed order.

| Order | Gate | Exact canonical locks / heads covered | Participating mutator modules |
|---:|---|---|---|
| 1 | Audio | `task041.audio_completion_ledger`, `task041.audio_workspace`, `task041.audio_gate_source` | `audio_completion_ledger_store.py`, `audio_workspace_store.py`, `audio_workspace_application.py`, `task041_audio_completion_gate_application.py` |
| 2 | Edit | `task043.project_save`, `task044.timeline`, `task044.edit_receipt` | `project_save.py`, `interactive_timeline_store.py`, `interactive_timeline_application.py`, `task044_edit_persistence_receipt.py` |
| 3 | Privacy | `task016.privacy_guard`, `task016.privacy_gate_source` | `privacy_guard.py`, `task016_privacy_gate_application.py` |
| 4 | Resource | `task020.resource_admission`, `task020.resource_gate_source` | `resource_admission_monitoring.py`, `task020_resource_gate_application.py` |
| 5 | Rights | already-held `task044.timeline`, then `task003.asset_registry`, `task003.rights_decision`, `task027.generation_lineage` | `store.py::SQLiteProductStore.register_asset` as the sole Asset-head commit seam, `task003_rights_gate_application.py`, `generation_output_adoption_application.py`, `production_control_store.py`, `production_proposal_store.py` |

The source-coordinate closure is exact:

| Gate | Receipt coordinates | Canonical head/mutation seam |
|---|---|---|
| Audio | source truth, role policy, canonical completion, ledger head | TASK-041 completion ledger store/application |
| Audio | workspace snapshot | TASK-041 Audio Workspace store/application |
| Edit | Project Manifest and ProjectSave terminal | TASK-043 ProjectSave coordinator |
| Edit | Timeline/edit snapshot/history head | TASK-044 Timeline store/application/edit receipt |
| Privacy | policy/input/evaluation/Human review/redaction/publication/invalidation | TASK-016 Privacy Guard + Gate source application |
| Resource | policy/observation/admission/operation Gate/incident | TASK-020 Resource Admission + Gate source application |
| Rights | Timeline source set | already-held TASK-044 Timeline head |
| Rights | Asset registry snapshot and every Asset identity/restriction | `store.py::SQLiteProductStore.register_asset`; every caller including ingest and derived-Asset paths passes this seam |
| Rights | rights policy/decision/revocation | TASK-003 Rights Gate source application |
| Rights | TASK-027 generation lineage | generation adoption, Production Control and Proposal stores |

No source coordinate may be derived from a store/head absent from this table.
All low-level mutation seams above participate even when called by a new or
existing higher-level application, so callers cannot bypass invalidation by
skipping a UI/application helper.

For an E-C-enabled Project, trusted TASK-043 Product composition injects an
exact `FinalGateProjectBinding` into `SQLiteProductStore`:

```text
binding_version = 1.0.0
record_type = FinalGateProjectBinding
task_owner = TASK-043
project_id/project_manifest_sha256
canonical_project_root_identity_sha256
asset_store_database_identity_sha256
final_gate_dispatch_admission_key_sha256
binding_sha256
```

The identities are body-free hashes, never host paths. They are derived from
the canonical opened Project Manifest/root/database by trusted composition, not
caller metadata. `SQLiteProductStore.register_asset` revalidates the manifest,
database identity and Project-local admission key before taking the Gate. An
E-C-enabled store opened without this binding, with another Project's binding,
or through an arbitrary CLI/path fails closed. A legacy Project without an E-C
binding may retain legacy Asset behavior but cannot produce E-C owner PASS or
enter E-C Export dispatch. Both direct callers, `ingest.py` and
`derived_assets.py`, must pass through this same low-level check.

Each participating upstream mutation uses an owner-local append-only
`OwnerGateInvalidationJournal` while these locks are held:

```text
journal_version = 1.0.0
record_type = OwnerGateInvalidationJournal
task_owner/gate_id
journal_id/project_id/mutation_operation_id
mutation_intent_sha256
pre_upstream_head_sha256s          exact owner-key map
post_upstream_head_sha256s         null in PREPARED; exact map afterward
pre_gate_source_head_sha256
gate_invalidation_record_sha256    null until INVALIDATION_COMMITTED
state = PREPARED | ABORTED_NO_UPSTREAM_WRITE | UPSTREAM_COMMITTED |
        INVALIDATION_COMMITTED
event_revision/parent_event_sha256
upstream_mutation_applied
upstream_effect_replayed = false
dispatch_started = false
event_sha256
```

State nullability is closed: PREPARED has null post-heads/null invalidation and
`upstream_mutation_applied=false`; ABORTED_NO_UPSTREAM_WRITE is terminal, has
post-heads exactly equal to pre-heads, null invalidation and `false`;
UPSTREAM_COMMITTED has exact changed post-heads, null invalidation and `true`;
INVALIDATION_COMMITTED has those post-heads, a nonnull invalidation SHA and
`true`. `parent_event_sha256` is null only at revision 1. Each successor
increments by one and keeps the same journal/mutation identity; unknown or
skipped states, forks and ID/body collisions are integrity errors.

The writer appends PREPARED before its canonical commit, records the exact
post-head after that commit, appends the Gate invalidation/source successor,
then records INVALIDATION_COMMITTED. On restart under the same locks, a
PREPARED journal whose current heads equal all pre-heads becomes
ABORTED_NO_UPSTREAM_WRITE with no invalidation and no replay. If the exact
`mutation_operation_id` is present in the canonical upstream store, recovery
derives its post-head and continues at UPSTREAM_COMMITTED; a changed head
without that exact operation is INTEGRITY_ERROR. Recovery after
UPSTREAM_COMMITTED finishes only the missing invalidation step and never
replays the upstream mutation. Any nonterminal journal makes that owner reader
`CURRENT_BLOCKED/RECOVERY_REQUIRED` and dispatch ineligible.

Under all locks, dispatch reparses every exact upstream head, owner Gate source
head and journal terminal, and requires them to equal the selected receipt/
reader coordinates before the Job CAS. Thus a Timeline/ProjectSave, Privacy,
Resource incident, Asset/restriction/Rights or generation-lineage mutation
linearizes wholly before or after dispatch admission; it cannot hide between a
PASS read and `DISPATCHING`. If any listed lock/head/hook is unavailable, the
reader is `SOURCE_UNAVAILABLE` and dispatch fails closed.

Dispatch re-reads all heads under the gate, creates a
`Task044ExportDispatchAdmissionReceipt` bound to their reader-result hashes,
the E-C Final Approval, Job version and export profile, then persists receipt +
`DISPATCHING` in one Job CAS. Revocation before CAS linearizes first and blocks.
Revocation after CAS does not cancel/replay the started effect; it stales
publication/future use and requires result reconciliation. No owner callback,
detector, collector, Provider or renderer runs while locks are held.

```text
receipt_version = 1.0.0
record_type = Task044ExportDispatchAdmissionReceipt
task_owner = TASK-044
receipt_id
project_id/project_manifest_sha256
timeline_id/timeline_revision/timeline_sha256
scene_epoch/scene_epoch_binding_sha256
final_approval_receipt_sha256
owner_gate_receipt_sha256s          exact five-key map
owner_reader_result_sha256s         exact five-key map
owner_store_head_sha256s            exact five-key map
export_operation_id/export_job_id
prepared_job_revision
committed_job_revision
export_profile_sha256
logical_output_identity
admission_state = ADMITTED_DISPATCHING
admitted_by/admitted_at
renderer_started = false
publication_release_deploy_activation_authorized = false
receipt_sha256
```

The receipt ID is deterministic over the full canonical body except timestamps
and final SHA; `admitted_at` is the Job CAS event time. The same CAS advances
exactly `prepared_job_revision -> committed_job_revision` and stores the
receipt plus `DISPATCHING`. Replay returns the same receipt only for identical
Job/version/body. Cross-Job/profile/result scope, head drift before CAS, ID/body
collision or already-advanced incompatible state fails with zero new dispatch.

The canonical TASK-043 durable Job ABI is amended narrowly: existing v1.0
non-EXPORT rows remain byte-for-byte readable/writable unchanged; an EXPORT Job
v1.1 row has `job_record_version=1.1.0` and adds
the full exact `Task044ExportDispatchAdmissionReceipt`. Pre-dispatch EXPORT Jobs
remain exact v1.0 rows where this field and discriminator are absent; the
`READY -> DISPATCHING` CAS creates the v1.1 variant with the receipt nonnull. It
is illegal for non-EXPORT Jobs. Under the expected Job
revision lock, `DurableProductJobService.transition` computes the one CAS event
time, constructs the receipt with `prepared_job_revision` and exact
`committed_job_revision = prepared + 1`, validates its ID/SHA, and writes the
nested receipt plus `DISPATCHING` in the same atomic Job record. There is no
prewritten receipt/sidecar and therefore no orphan/admission ambiguity; an
application-side second write cannot satisfy the contract.

A v1.0 EXPORT Job in QUEUED or PREFLIGHT retains its exact legacy pre-effect
transitions. READY may upgrade only in the explicit `READY -> DISPATCHING` CAS
after full current-source revalidation. HUMAN_REQUIRED with `attempt=0` and no
dispatch/effect evidence may follow only its existing pre-effect recovery back
to PREFLIGHT/FAILED/CANCELLED, and can upgrade later only after reaching READY.
DISPATCHING, RUNNING, UNKNOWN, HUMAN_REQUIRED with any dispatch/effect evidence,
and terminal SUCCEEDED/FAILED/CANCELLED remain readable legacy history or
reconciliation evidence but are ineligible for E-C dispatch, Final Approval
reuse or silent migration. Existing v1.0 non-EXPORT bytes and behavior remain
unchanged. Any v1.0 state/evidence combination not classified here fails
closed.

## 5. TASK-036 consume-only Final Approval v2

TASK-036 calls all five readers for readiness, approval prepare and approval
apply. It accepts only the exact owner matrix, identical Project/Timeline/Scene
epoch scope, five `CURRENT_PASS` results and no effect inflation. It stores no
private owner source bodies.

```text
receipt_version = 2.0.0
record_type = EcFinalReviewApprovalReceipt
task_owner = TASK-036
receipt_id
project_id/project_manifest_sha256
timeline_id/timeline_revision/timeline_sha256
scene_epoch/scene_epoch_binding_sha256
readiness_projection_sha256
owner_gate_receipt_sha256s      exact five-key map
owner_reader_result_sha256s     exact five-key map
decision = APPROVE
approved_by/approved_at
export_job_created = false
render_or_publish_started = false
receipt_sha256
```

The existing TASK-036 Human prepare/confirm/apply appends it. Apply re-reads all
owner results and readiness bytes; change consumes/rejects the token. Existing
v1 wrappers/approvals are readable history but are ineligible for a new E-C
Export Job.

## 6. UI transitions

| Gate | MISSING/blocked navigation | PASS display |
|---|---|---|
| Audio | Audio workspace; canonical completion未発行 | `Audio current` |
| Privacy | Privacy Review | `Privacy current` |
| Resource | Resource readiness | `Resource current` |
| Rights | Asset Rights Review / explicit Human decision | `Rights current` |
| Edit | Edit recovery/history | `Edit current` |

Final Approval is enabled only for five current owner results on the post-E-C3
Timeline. There is no force-PASS, fixture upload or cached fallback.

## 7. Restart/failure and negative matrix

- Restart reopens every owner source store and derives a new reader result.
- Pending metadata/rights/approval confirmations disappear safely.
- Fork/gap/malformed/cross-scope source becomes integrity error/UNKNOWN.
- Owner recovery never causes TASK-036 to issue an owner receipt.
- Successor/invalidation stales approval without deleting history/Job.

| Case | Result | Effect |
|---|---|---:|
| synthetic TASK-036 PASS/v1 wrapper | ineligible | 0 |
| TASK-041 diagnostic candidate only | Audio MISSING | 0 |
| owner writer/type mismatch or missing Gate | reject/blocked | 0 |
| reader result missing/wrong/unknown record type | reject/blocked | 0 |
| historical PASS after successor | current_valid false | 0 |
| fork/gap/multiple latest/cap+1 | owner integrity error | 0 |
| Privacy without exact Human review | blocked | 0 |
| Resource PASS treated as dispatch lease | forbidden/static failure | 0 |
| Rights writer TASK-027 or rights UNKNOWN | reject/blocked | 0 |
| revocation before dispatch CAS | dispatch blocked | 0 |
| revocation after DISPATCHING CAS | preserve effect; publication stale | 0 new/replay |
| owner change between approval prepare/apply | token consumed; no approval | 0 |
| dispatch receipt cross-Job/profile/head or replay drift | integrity/recovery block | 0 new |
| non-EXPORT/v1.0 Job bytes change or gain admission fields | compatibility failure; PR blocked | 0 |
| EXPORT DISPATCHING without same-record full admission receipt | transition reject | 0 dispatch |
| nested admission receipt ID/SHA/revisions/time differs from Job CAS | transition/parser reject | 0 dispatch |
| v1.0 EXPORT already DISPATCHING/terminal silently upgraded | compatibility/integrity reject | 0 new |
| v1.0 EXPORT RUNNING/UNKNOWN or post-effect HUMAN_REQUIRED upgraded | compatibility/integrity reject | 0 replay/new |
| v1.0 EXPORT unclassified state/effect combination | fail closed | 0 |
| Privacy/Resource/Timeline/Asset upstream commit races dispatch | one linearization order; stale blocks or post-CAS reconciliation | 0 replay |
| upstream commit crashes before Gate invalidation | nonterminal journal blocks dispatch; recover invalidation only | 0 upstream replay/dispatch |
| crash after PREPARED with unchanged upstream heads | terminalize ABORTED_NO_UPSTREAM_WRITE | 0 upstream/invalidation/dispatch |
| PREPARED recovery sees unrelated changed head | INTEGRITY_ERROR | 0 replay/dispatch |
| E-C Asset store binding missing/cross-Project/DB mismatch | register reject before write | 0 Asset/dispatch |
| direct ingest/derived/CLI Asset registration races dispatch | universal store seam linearizes or rejects | 0 hidden mutation/replay |

## 8. Future implementation Allowed Files

### TASK-081-A Audio

- `src/ai_video_production/audio_completion_ledger_store.py`
- `src/ai_video_production/audio_workspace_store.py`, only for workspace-head
  admission/invalidation participation
- `src/ai_video_production/audio_workspace_application.py`, only for the same
  protocol integration
- new `src/ai_video_production/task041_audio_completion_gate_application.py`
- new `src/ai_video_production/task041_audio_final_gate.py`
- new `schemas/task041-audio-final-gate.schema.json`
- new `src/ai_video_production/schema_resources/task041-audio-final-gate.schema.json`
- new `tests/test_task041_audio_completion_gate_application.py`
- new `tests/test_task041_audio_final_gate.py`
- `tests/test_task041_audio_workspace_store.py`
- `tests/test_task041_audio_workspace_application.py`

### TASK-081-B Privacy

- `src/ai_video_production/privacy_guard.py`
- new `src/ai_video_production/task016_privacy_gate_application.py`
- new `src/ai_video_production/task016_privacy_final_gate.py`
- new `schemas/task016-privacy-final-gate.schema.json`
- new `src/ai_video_production/schema_resources/task016-privacy-final-gate.schema.json`
- new `tests/test_task016_privacy_gate_application.py`
- new `tests/test_task016_privacy_final_gate.py`

### TASK-081-C Resource

- `src/ai_video_production/resource_admission_monitoring.py`
- new `src/ai_video_production/task020_resource_gate_application.py`
- new `src/ai_video_production/task020_resource_final_gate.py`
- new `schemas/task020-resource-final-gate.schema.json`
- new `src/ai_video_production/schema_resources/task020-resource-final-gate.schema.json`
- new `tests/test_task020_resource_gate_application.py`
- new `tests/test_task020_resource_final_gate.py`

### TASK-081-D Rights

- new `src/ai_video_production/task003_rights_gate_application.py`
- new `src/ai_video_production/task003_rights_final_gate.py`
- `src/ai_video_production/assets.py`, only for Asset-head Gate/invalidation
  protocol participation and read projection
- `src/ai_video_production/store.py`, only to make
  `SQLiteProductStore.register_asset` the
  universal Asset-head Gate/invalidation seam
- `src/ai_video_production/derived_assets.py`, only to carry the trusted Project
  binding through its direct Asset registration path
- `src/ai_video_production/ingest.py`, only to participate in the Gate/
  invalidation protocol for Asset-head mutation
- `src/ai_video_production/generation_output_adoption_application.py`, only for
  generation-lineage invalidation participation
- `src/ai_video_production/production_control_store.py`, only for
  Candidate/Asset lineage invalidation participation
- `src/ai_video_production/production_proposal_store.py`, only for Proposal/
  generation-lineage invalidation participation
- new `schemas/task003-rights-final-gate.schema.json`
- new `src/ai_video_production/schema_resources/task003-rights-final-gate.schema.json`
- new `schemas/task003-rights-license-decision.schema.json`
- new `src/ai_video_production/schema_resources/task003-rights-license-decision.schema.json`
- new `tests/test_task003_rights_gate_application.py`
- new `tests/test_task003_rights_final_gate.py`
- `tests/test_assets_and_store.py`
- new `tests/test_task081_asset_gate_binding.py`

### TASK-081-E Edit/protocol/TASK-036 consumer

- `src/ai_video_production/task044_edit_persistence_receipt.py`
- `src/ai_video_production/project_save.py`, only for dispatch/invalidation
  protocol participation
- `src/ai_video_production/interactive_timeline_store.py`, only for dispatch/
  invalidation protocol participation
- `src/ai_video_production/interactive_timeline_application.py`, only for
  dispatch/invalidation protocol participation
- new `src/ai_video_production/final_gate_dispatch_protocol.py`
- `src/ai_video_production/export_queue_application.py`, only to integrate the
  dispatch admission receipt and `DISPATCHING` in the same Job CAS
- `src/ai_video_production/durable_product_job.py`, only for the versioned
  EXPORT admission fields and atomic transition CAS
- `schemas/durable-product-job.schema.json`
- `src/ai_video_production/schema_resources/durable-product-job.schema.json`
- new `schemas/final-gate-dispatch-protocol.schema.json`
- new `src/ai_video_production/schema_resources/final-gate-dispatch-protocol.schema.json`
- `src/ai_video_production/final_review_gate.py`
- `src/ai_video_production/final_review_readiness.py`
- `src/ai_video_production/final_review.py`
- `src/ai_video_production/final_review_application.py`
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/task036_trusted_launcher.py`
- new `tests/test_task044_final_gate_dispatch_protocol.py`
- `tests/test_task044_export_queue.py`
- `tests/test_task043_durable_product_job.py`
- `tests/test_task043_project_save_recovery.py`
- `tests/test_task044_interactive_timeline.py`
- `tests/test_task003_asset_ingest.py`
- `tests/test_task016_privacy_guard.py`
- `tests/test_task020_resource_admission_monitoring.py`
- `tests/test_task036_final_review_gate.py`
- `tests/test_task036_final_review_readiness.py`
- `tests/test_task036_final_review.py`
- `tests/test_task036_final_review_application.py`
- `tests/test_task036_final_review_shell.py`

`tests/test_task044_final_gate_dispatch_protocol.py` must include deterministic
barrier races for Privacy invalidation, Resource incident, Timeline/
ProjectSave commit and Asset/restriction mutation both immediately before and
immediately after the Job CAS, plus crash recovery at every invalidation-journal
state.

`tests/test_task081_asset_gate_binding.py` must cover trusted canonical binding,
missing binding, another Project/root/database, forged `source_project`, direct
store caller, ingest caller, derived-Asset caller and a barrier race against
dispatch CAS.

Documentation is limited to these TASK-081 paths: new
`docs/ai-team/tasks/TASK-081/task.md`, new
`docs/ai-team/tasks/TASK-081/ec4-implementation-evidence.md`,
`docs/ai-team/current-state.md`, and `docs/ai-team/task-index.md`. Any runtime
path outside these lists returns to Critic before mutation.

## 9. Prohibited effects

No media read, detector/OS collection, reservation, rights-field rewrite,
redaction, Provider/paid/native call, Timeline/Resolve write, actual Final
Approval, Export enqueue/dispatch, publication, Release, Deploy or Activation
is authorized by TASK-078.

## 10. Handoff

Implementation DAG is E-C1 -> E-C4 owner apps/readers. Runtime evaluation is
E-C3 resulting Timeline -> E-C4 results -> E-C5 Final Approval. Handoff requires
reachable owner source applications, canonical TASK-041 source decision,
TASK-003-only Rights writer, TASK-036 consume-only, linearized dispatch/
revocation races and residual C/H `0 / 0`.
