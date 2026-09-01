# E-C1 — Scene Epoch Downstream Binding

- Candidate Task identity: `TASK-079`
- Integration owner: `TASK-027`
- Amendment owners: `TASK-027`, `TASK-013`, `TASK-037`, `TASK-036` only
- DEV profile: `DEV-4`
- Dependency: canonical public TASK-077 development-completion receipt on canonical main
- Effect authority in this design: `NONE`

## 1. Goal and ownership

Bind every new AI Video downstream record to one current Scene epoch without
creating a second Scene store. TASK-027 remains the sole runtime owner of the
Proposal structure epoch, GO/Scene finalization and downstream orchestration
binding. TASK-077 is only the cross-owner development amendment that must merge
before E-C1 implementation begins. TASK-013 consumes the TASK-027 binding for
execution, TASK-037 retains it in Candidate/Slot lineage and stale truth, and
TASK-036 projects it read-only.

No TASK-003, TASK-038, Timeline, Export, Provider adapter or owner-Gate file is
modified by E-C1.

## 2. Public dependency handshake

E-C1 does not prescribe TASK-077 private implementation. Its later merged
public *development completion receipt* is an implementation-start Gate only;
it is never Product Scene truth and is not consumed as Human finalization
authority. It must expose at minimum:

```text
receipt_version
task_owner = TASK-077
receipt_id
merged_commit_sha256
public_amendment_contract_version
public_amendment_contract_sha256
task027_schema_sha256
task037_schema_sha256
task036_consumer_contract_sha256
focused_validation_evidence_sha256
state = COMPLETED
completed_at                canonical UTC
all_effects_started = false
receipt_sha256
```

If the public completion format uses a different exact type/name, its public
contract must provide an adapter with the same development-Gate semantics.
E-C1 must not infer fields from a private branch, mutable UI state or the old
P-UX-2B3 receipt. Once the Gate is satisfied, every runtime read below comes
from TASK-027/TASK-037 canonical Product stores.

The completion receipt is checked only by TASK-079 implementation/build-entry
tests. Packaged runtime never requires, opens or reparses that development
artifact. Its SHA may remain inside the TASK-027 v2 receipt/binding as opaque
amendment provenance already sealed at build/implementation time; absence of
the original TASK-077 document in a clean Product profile cannot block F3.

The runtime source is TASK-027's amended `Task027SceneFinalizationReceiptV2`,
which retains the existing `finalization_id`, `plan_id`, Proposal and Blueprint
coordinates and adds the TASK-077 public amendment fields:

```text
receipt_version = 2.0.0
record_type = Task027SceneFinalizationReceiptV2
task_owner = TASK-027
project_id/finalization_id/plan_id
proposal_id/proposal_revision/proposal_sha256
blueprint_id/blueprint_sha256
scene_ledger_sha256/scene_set_root_sha256
scene_epoch                         explicit integer >= 0
scene_structure_operation_commitment_sha256  null only for root/no-operation epoch
task077_public_completion_receipt_sha256
finalized_by
receipt_sha256
```

TASK-027 prepare/apply revalidates the current Human GO-approved Plan, exact
Proposal/Blueprint/ledger/set root and epoch under its existing CAS. A later
Proposal revision makes the historical receipt noncurrent; TASK-077 cannot
mint, refresh or invalidate this runtime receipt.

## 3. Receipt ABI owned by TASK-027

`SceneEpochDownstreamBinding` is embedded in the canonical TASK-027 Queue
snapshot and repeated by hash in every affected record. It is not a new store.

```text
binding_version = 1.0.0
record_type = SceneEpochDownstreamBinding
task_owner = TASK-027
binding_id
project_id
proposal_id
proposal_revision
proposal_sha256
scene_id
scene_record_sha256
scene_ledger_sha256
scene_set_root_sha256
scene_epoch                    >= 0 and explicitly present
task077_public_completion_receipt_sha256
task027_scene_finalization_id
task027_scene_finalization_receipt_sha256
scene_structure_operation_commitment_sha256 nullable only for a root/no-operation epoch
binding_state = CURRENT
provider_execution_authorized = false
candidate_mutation_authorized = false
timeline_mutation_authorized = false
binding_sha256
```

`binding_id` is deterministic over Project/Proposal/Scene/epoch, the TASK-027
Scene-finalization receipt and TASK-077 amendment-provenance SHA. Identical
canonical bytes reproduce the binding; an ID
collision with different bytes or a binding sidecar not present in the Queue
snapshot is rejected.

One Queue snapshot may contain multiple Scene bindings, canonically sorted by
`scene_id`. The binding is valid only after TASK-027 reparses the canonical
current Proposal/Blueprint Scene ledger, proves `scene_ledger_sha256` and
`scene_set_root_sha256`, recomputes the selected full Scene record's
`scene_record_sha256` and proves that exact `scene_id + scene_record_sha256` is
a member. A receipt hash alone is never membership proof. If the current
TASK-027 Scene-finalization receipt and canonical Proposal ledger source cannot
expose the set root and canonical ledger read coordinates, E-C1 remains effect
zero; the TASK-077 development receipt is amendment provenance only. Duplicate
Scene IDs, mixed Project/Proposal/ledger/epoch coordinates or more than 256 Scene bindings
reject the whole snapshot.

### Owner amendments

- TASK-027 Queue entry v1.2 adds `scene_epoch_binding_sha256` and copies
  `scene_epoch`; admission re-reads the current TASK-027 Proposal and
  Scene-finalization receipt. The TASK-077 SHA is version provenance only.
- TASK-013 execution event v2 adds the same two fields to `DISPATCHING` and
  terminal events. Apply revalidates after preflight and before persisting
  `DISPATCHING`.
- TASK-037 generated-video Candidate lineage adds the exact binding hash and
  epoch. A Scene successor makes the old generated-video Candidate/Slot
  projection STALE; it never changes the current Scene receipt.
- TASK-036 visual handoff and Shell projection display current/stale/missing
  epoch and navigate to the owning page; they mint no binding.

## 4. Old epoch effect-zero rule

For the new generated-video lane, an explicitly present epoch `0` is valid when
the current canonical Proposal is still epoch `0`. Any record with an absent
epoch, an epoch lower than the current canonical epoch, an epoch jump/parent
commitment mismatch or a non-current public receipt is history-only. The
following *new downstream effects admitted after stale determination* must be
exactly zero:

```text
provider_preflight_started_after_stale
provider_execution_started_after_stale
output_adoption_started
audit_promotion_started
human_accept_or_lock_created
timeline_write_started
final_approval_created
export_job_created
render_or_publish_started
```

An effect already admitted while the epoch was current remains immutable
historical evidence. If Provider dispatch was already persisted, an epoch
change does not rewrite its count to zero, cancel it or replay it. Recovery may
append the exact historical terminal event; provider re-execution remains zero,
and adoption/Audit/LOCK/placement/approval/export from that old terminal remain
zero. An append-only STALE metadata transition is allowed only through the canonical
TASK-037 stale mechanism and is not a Provider/Timeline/Export effect. Existing
IMAGE records and P-UX-2H behavior are not reinterpreted as legacy E-C records.

## 5. UI transitions

| Current state | TASK-036 display | Only next action |
|---|---|---|
| TASK-027 finalization receipt unavailable/stale | `Scene確定receipt待ち` | open TASK-027 Scene workspace |
| receipt valid, binding missing | `下流binding未作成` | prepare TASK-027 Queue admission |
| binding current, no Queue row | `AI動画Job準備完了` | open AI Video Queue |
| old/mismatched epoch | `Scene更新によりSTALE` | return to Planning/Scene; never run old Job |
| chain fork/gap/tamper | `Scene履歴の整合性エラー` | recovery/help only |

UI never offers a “continue anyway” path for an old epoch.

## 6. Restart and failure

- Pending confirmations are process-local and disappear safely on restart.
- Durable Queue/execution/Candidate projections are reconstructed from their
  owner stores and the current TASK-027 Proposal/finalization receipt. The
  merged TASK-077 completion SHA is immutable amendment provenance.
- If the TASK-027 Proposal/finalization source is unavailable, currentness is
  `UNKNOWN`, not cached PASS; all effects remain zero.
- A Scene revision during Queue prepare/apply consumes and rejects the token.
- A Scene revision after `DISPATCHING` does not cancel or replay a provider.
  The terminal output, if later observed, remains old-epoch evidence and cannot
  be adopted.
- Fork, gap, duplicate epoch, parent mismatch and lower epoch after a higher
  epoch are data-integrity failures requiring owner recovery.

## 7. Negative matrix

| Case | Result | Effect count |
|---|---|---:|
| TASK-077 public development completion missing at implementation start | implementation Gate blocked | 0 |
| TASK-027 runtime finalization receipt missing/stale | `BLOCKED_SCENE_RECEIPT` | 0 |
| private/unmerged receipt supplied | reject non-canonical source | 0 |
| missing epoch on new generated-video row | invalid legacy history only | 0 |
| explicit epoch 0 while current epoch is 0 | current and eligible after all other Gates | n/a |
| explicit epoch 0 while current epoch >0 | `STALE_SCENE_EPOCH` | 0 |
| cross Project/Proposal/Scene | data-integrity reject | 0 |
| valid receipt plus non-member Scene ID/record | membership reject | 0 |
| duplicate Scene binding | whole snapshot reject | 0 |
| stale confirmation after Scene revision | authorization reject; token consumed | 0 |
| old epoch terminal output | adoption ineligible | 0 |
| dispatch began before epoch changed | preserve started evidence; no replay | 0 new Provider/adoption effects |
| old epoch ACCEPT/LOCK attempt | TASK-037 stale reject | 0 |
| old epoch placement/Final Approval/Export | exact blocker | 0 |
| unknown field/version downgrade/cap+1 | fail closed | 0 |

## 8. Future implementation Allowed Files

- `src/ai_video_production/generation_queue_application.py`
- `src/ai_video_production/production_proposal.py`
- `src/ai_video_production/planning_application.py`
- `src/ai_video_production/approved_plan_orchestration.py`
- `src/ai_video_production/creative_generation_execution_application.py`
- `src/ai_video_production/production_control.py`
- `src/ai_video_production/production_control_store.py`
- `src/ai_video_production/visual_generation_handoff.py`
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/task036_shell_v611.py`
- new `schemas/scene-epoch-downstream-binding.schema.json`
- new `src/ai_video_production/schema_resources/scene-epoch-downstream-binding.schema.json`
- `schemas/production-proposal-revision.schema.json`
- `src/ai_video_production/schema_resources/production-proposal-revision.schema.json`
- `docs/ai-team/tasks/TASK-037/schemas/production-control-asset-registry.schema.json`
- `tests/test_task027_generation_queue_application.py`
- `tests/test_task013_creative_generation_execution_application.py`
- `tests/test_task037_production_control.py`
- `tests/test_task037_production_control_store.py`
- `tests/test_task036_visual_generation_handoff.py`
- `tests/test_task027_production_proposal.py`
- `tests/test_task027_planning_application.py`
- `tests/test_task036_shell_ui.py`
- `tests/test_task036_v611_visual_contract.py`
- new `docs/ai-team/tasks/TASK-079/task.md`
- new `docs/ai-team/tasks/TASK-079/ec1-implementation-evidence.md`
- `docs/ai-team/current-state.md`
- `docs/ai-team/task-index.md`

Any need outside this list returns to design Critic before mutation. In
particular, TASK-077, Asset, Audit, Timeline, Export and owner-Gate files are
forbidden.

## 9. Prohibited effects

Provider/free/paid/native execution, media read, Asset ingest, Candidate Human
decision/LOCK, Timeline/Resolve mutation, owner Gate issuance, Final Approval,
Export enqueue/dispatch, Release, Deploy and Activation are all prohibited.

## 10. Handoff

E-C1 hands E-C2 and E-C4 one merged Product ABI: current TASK-027
`SceneEpochDownstreamBinding.binding_sha256` plus exact Project/Proposal/Scene/epoch
coordinates. Handoff is ready only when old-epoch effect-zero negatives pass,
TASK-077 public development completion is proven without private-diff access, all
four owner amendments are restart-safe and residual C/H is `0 / 0`.
