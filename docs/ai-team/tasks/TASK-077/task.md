# TASK-077 — Scene Structure Gate Integration

## Bound state

- Date: `2026-09-01`
- Canonical base: `1c9c19fa1f174934ced26aba66c1f447cd0d7bf1`
- Worktree / branch: `task-077-scene-structure-gate-design` /
  `codex/task-077-scene-structure-gate-design`
- Development profile: `DEV-3 HIGH ASSURANCE`
- Status: `DESIGN_DRAFT / IMPLEMENTATION_STOP_CROSS_OWNER_PROTOCOL_AND_CRITIC_REQUIRED`

This design was freshly rebound after PR #490 merged.  The intervening main
changes are the central model readback test and TASK-074 voice authority paths;
neither overlaps this task's candidate Scene structure, Production transaction,
or Shell bridge paths.  This rebind grants no implementation authority.

## Objective and non-effects

TASK-077 integrates a bounded, safe Scene add/delete operation while preserving
the existing canonical responsibilities:

- TASK-027 remains the owner of append-only Planning Proposal revisions, Human
  confirmation, GO/finalization invalidation, and the active Blueprint.
- TASK-037 remains the owner of Production Slots, Candidates, dependency edges,
  Plan installation, Candidate registration, and WORLD LOCK mutation.
- TASK-036 remains a typed Shell consumer only.  It never writes either store.

The operation applies only while the exact Production graph is empty.  It does
not call a Provider, authorize paid work, create Assets or Candidates, mutate a
Timeline or external NLE, start native UI work, export, publish, delete, or
silently migrate an installed Project.

This task is a cross-owner amendment, not a replacement for the current
visual-only `prepare_scene_revision` / `apply_scene_revision` API.

## Verified current seam

`Task027PlanningApplication._scene_revision_blueprint` in
`src/ai_video_production/planning_application.py` rejects any Scene count,
order, or identity change.  Its `prepare_scene_revision` and
`apply_scene_revision` therefore remain visual/frame revision only.

`Task037ProductionControlApplication` in
`src/ai_video_production/production_control_application.py` exposes independent
`install_approved_plan`, `register_candidate`, `prepare_lock`, and `apply_lock`
mutators.  Its current `load` path and `ProductionControlSnapshotStore.save`
path do not provide a single caller-held read/proof/write transaction: `save`
acquires `_exclusive_snapshot_lock` internally in
`src/ai_video_production/production_control_store.py`.  Acquiring that same
non-reentrant lock around an existing public mutator risks deadlock, while a
status check before the mutator races with installation, Candidate registration,
and WORLD LOCK.

`Task036ShellBridge` currently offers only
`planning_prepare_scene_revision` and `planning_apply_scene_revision` in
`src/ai_video_production/task036_shell_ui.py`.  The Scene page in
`src/ai_video_production/task036_shell_v611.py` hard-disables add/remove.
`tests/test_task036_v611_visual_contract.py` correctly records that pre-gate
state.  No Scene structure API or `SceneStructureGate` exists in current
source.

## Closed future Application surface

Only a jointly allocated TASK-027/TASK-037 amendment may add the following
separate typed surface:

```text
scene_structure_status
prepare_scene_structure_revision
apply_scene_structure_revision
readback_scene_structure_revision
```

`scene_structure_status` returns a public-safe state, Japanese reason, and one
actionable next operation.  It distinguishes ready pre-install state, active
Production graph, stale snapshots, missing joint authority, and ambiguous
Project state.  Normal UI output contains no lock path, raw hash, store path,
or authority internals.

`prepare_scene_structure_revision` accepts exactly one closed operation:

- `ADD_SPLIT`
- `REMOVE_SELECTED_INTO_PREVIOUS`
- `REMOVE_SELECTED_INTO_NEXT`

The Shell obtains selected Scene identity and current projection only from its
bound Planning readback.  It never accepts a raw Project path, a user-entered
revision/hash, a full Blueprint, a Provider/model route, or store data.  The
Application seals the Project identity, current Proposal snapshot and parent,
active structure epoch, current Production snapshot, and exact empty graph
proof before it issues one Human confirmation.

For a split, the selected existing ID remains the left Scene and a deterministic
right ID is assigned from `SC01` through `SC99`, then `SC100` through `SC256`.
The lowest positive numeric reservation in that sequence wins.  A reservation
is extracted only from `^SC0*([1-9][0-9]*)(?:$|[-_][A-Za-z0-9][A-Za-z0-9._-]*)$`:
therefore canonical `SC01`, zero-padded alias `SC001`, and suffixed legacy
`SC01-old` all reserve numeric value `1`.  Any current Scene ID outside that
closed canonical-or-qualified-legacy grammar makes structure editing
unavailable/effect 0 until a separately authorized migration resolves it; it
cannot be silently ignored to free a potentially colliding number.  The
generated canonical spelling must also be absent.  The split is strictly interior, both
ranges contain at least one frame, the final ledger is gapless, and the count
is at most 256.  Both child semantic payloads are complete.  V2 requires explicit new inner `end_frame_intent` and
`start_frame_intent`; audio and all semantic fields are explicit, not cloned or
inferred.

For deletion, the requested direction fixes the surviving neighbour.  More than
one Scene is required; the receipt exposes the public-safe survivor/deleted
`scene_id` display identity and full replacement semantic payload.  `scene_id`
is a Product-facing Scene identity, while Project/store/lock/confirmation IDs,
raw snapshots, and authority coordinates remain technical details and are never
rendered in normal UI.  Historical Proposal revisions are
append-only and retain the deleted Scene.

`apply_scene_structure_revision` consumes the confirmation before the joint
transaction.  A stale or mismatch detected before the Proposal append is
`NO_WRITE_REJECTED`: it burns the confirmation and may be followed by a fresh
status and preparation.  An uncertainty after the Proposal append is instead
`RECOVERY_REQUIRED`: it burns the confirmation, permits matching commitment
readback only, and prohibits fresh preparation or any new split/merge for that
Project until readback reaches `APPLIED_EXACT` or proves the matching operation
performed no append.  There is no retry, recompute, rollback, migration,
cleanup, or reinstallation.  Successful readback shows the new Proposal
revision and explains in Japanese that GO, Scene finalization, and Plan review
must be performed again.

Apply outcome is not a binary success/error shortcut.  The Application records
three mutually exclusive result classes:

- `NO_WRITE_REJECTED`: validation or pre-append re-read failed; no Proposal
  append occurred and the burned confirmation cannot be reused.
- `APPLIED_EXACT`: the Proposal append committed and the immediate readback
  verifies the exact sealed child revision and operation commitment.
- `AMBIGUOUS_AFTER_PROPOSAL_WRITE`: the append may have committed but immediate
  readback failed or became unavailable.  It asserts neither success nor
  no-change, performs no rollback or second apply, and is
  `RECOVERY_REQUIRED`.

Every structure child revision must persist the sealed
`scene_structure_operation_commitment_sha256` in the TASK-027 Proposal record.
It binds the parent Proposal hash/revision, prior epoch, selected public Scene
identity, closed operation kind, canonical typed operation-payload hash, and
pre-install Production proof hash.  `readback_scene_structure_revision` is
read-only: it verifies this persisted commitment against the sealed operation
coordinate and child revision.  It may resolve an `APPLIED_EXACT` receipt after
restart, but it never prepares, applies, or recreates an operation.  A caller
cannot substitute a path, snapshot, epoch, or operation payload to turn an
ambiguous result into a second split/merge.

## Cross-owner linearization requirement

Before source implementation, TASK-027 and TASK-037 must allocate a single
per-Project `SceneStructureGate` protocol and a transaction-capable TASK-037
read/proof boundary.  The fixed order is:

```text
SceneStructureGate
  -> TASK-027 application lock
  -> TASK-037 transaction-capable Production snapshot lock
  -> Proposal store's own internal commit lock, only inside save
```

All Production mutators—Plan installation, Candidate registration,
`mark_ready_for_audit`, and both WORLD LOCK preparation/application paths—must
enter the gate before their Production transition.  Plan consumers must require the active Proposal
revision and structure epoch, not only a historical Approved Plan.

The Production transaction boundary must make the current graph proof and its
CAS currentness linearizable without nesting the existing public
`ProductionControlSnapshotStore.save` lock.  The exact internal implementation
symbol or a new shared module is **not allocated by this design** and must be
bound by the cross-owner amendment before code starts.

Likewise, `Task027PlanningApplication`'s application lock is not the
`ProductionProposalSnapshotStore.save` lock.  A structure operation must never
pre-acquire either store's non-reentrant internal `_exclusive_snapshot_lock`
then call the existing public save method.  It holds the gate and application
lock while it obtains the TASK-037 empty proof; because structure apply does
not write TASK-037, it then appends through the Proposal store's normal
internally locked CAS save.  The joint protocol must test both lock orderings
against ordinary revision, GO, Scene-finalization, Plan installation, Candidate
registration, `mark_ready_for_audit`, and WORLD LOCK mutations, with no nested
same-lock acquisition or deadlock.

Structure apply holds the order above, re-reads all sealed commitments under the
joint protocol, and appends exactly one TASK-027 Proposal revision.  It does
not clear, rewrite, migrate, install, or otherwise change TASK-037 state.
Any nonempty, installed, stale, unknown, mismatched, or ambiguous Production
graph returns disabled/effect 0 with a Japanese recovery action.

## Downstream invalidation and UI migration

The canonical owner of the structure epoch is the append-only TASK-027
`ProductionProposalRevision` record.  The field is an explicit nonnegative
integer, not an inferred default: newly created root Proposal revisions write
epoch `0`; ordinary child revisions retain their parent's exact epoch; a
successful structural child increments it by exactly one.  The same record
persists the operation commitment described above and its hash participates in
the Proposal identity.

An old Project/Proposal that lacks this explicit field is not silently treated
as epoch `0`.  `scene_structure_status` returns unavailable/effect 0 and the
Project remains on existing visual-only Scene revision behavior until a
separately authorized migration exists.  TASK-077 has no migration authority.

Every `ApprovedProductionPlan`, Scene-finalization receipt, and TASK-037 Plan
consumer must bind and compare the exact Proposal revision, Proposal SHA, and
structure epoch.  A successful structural revision therefore marks prior GO,
Scene-finalization receipt, and Approved Plan unusable while retaining them as
historical evidence.  `ApprovedPlanVerifier.require_current`, installer, and
generation consumers must reject an older revision/epoch rather than
auto-refresh it.

Migration is deliberately staged:

1. Preserve `test_scene_add_remove_remain_disabled_and_finalization_is_exactly_bound`
   unchanged while no joint gate is available.
2. Add companion TASK-027/TASK-037 API and race tests before changing the Shell.
3. Once the joint protocol is passing, split the legacy visual test into two
   retained obligations: a status-driven add/remove regression where controls
   remain disabled whenever public status is not ready, and the existing
   finalization exact-binding regression with all current prepare/apply and
   sealed-snapshot assertions.  Never simply delete either obligation.
4. Add strict TASK-036 bridge methods rather than overloading visual
   `planning_prepare_scene_revision`; handlers submit once, refresh canonical
   readback, and expose no raw IDs/hashes in the normal view.

The new controls must use Japanese user language and precise recovery actions:
for example, a nonempty Production graph directs the user to review the
existing plan/production state rather than suggesting deletion.  The Scene
page continues to consume central Settings > AI models read-only; it adds no
page-local selector or save action.

## Allowed-file candidates — verified existing paths only

The following are candidates, not implementation authorization.  Any addition,
including the gate's eventual physical module path, requires the joint owner
allocation and fresh overlap/lock check.

| Responsibility | Verified candidate paths / symbols |
| --- | --- |
| TASK-027 structure schema/API, confirmation, invalidation | `src/ai_video_production/production_proposal.py`: `ProductionProposalRevision`, `ApprovedProductionPlan`, `ProductionProposalRegistry`; `src/ai_video_production/planning_application.py`: `_scene_revision_blueprint`, `prepare_scene_revision`, `apply_scene_revision`, `prepare_install_plan`, `apply_install_plan` |
| TASK-027 Proposal persistence | `src/ai_video_production/production_proposal_store.py`: `ProductionProposalSnapshotStore.save` |
| Active Plan verification/installation | `src/ai_video_production/approved_plan_orchestration.py`: `ApprovedPlanVerifier.require_current`, `ApprovedPlanProductionControlInstaller.install` |
| TASK-037 transaction/gate integration | `src/ai_video_production/production_control_application.py`: `install_approved_plan`, `register_candidate`, `mark_ready_for_audit`, `prepare_lock`, `apply_lock`; `src/ai_video_production/production_control_store.py`: `_exclusive_snapshot_lock`, `ProductionControlSnapshotStore.save` |
| TASK-036 typed bridge and presentation | `src/ai_video_production/task036_shell_ui.py`: `Task036ShellBridge.planning_prepare_scene_revision`, `planning_apply_scene_revision`; `src/ai_video_production/task036_shell_v611.py`: `renderScenes`, `reviseScene`, current add/remove controls |
| Focused tests | `tests/test_task027_planning_application.py`, `tests/test_task037_production_control_application.py`, `tests/test_task036_shell_ui.py`, `tests/test_task036_v611_visual_contract.py` |

Do not modify shared current-state, task-index, roadmap, CHANGELOG, existing
dirty worktrees, Provider/native/GUI paths, or TASK-076.

## Required focused and negative matrix

| ID | Assertion |
| --- | --- |
| SSG-01 | `scene_structure_status` is public-safe and disabled for missing joint authority, nonempty/installed/unknown Production state, stale Proposal, and ambiguous Project. |
| SSG-02 | Split succeeds only pre-install with a sealed empty-graph proof; left ID is stable, right ID follows the exact `SC01..SC99, SC100..SC256` occupancy rule, ledger is gapless, and count 257 is rejected. |
| SSG-03 | Split rejects boundary frames, bool/non-int frames, duplicate/forged IDs, `SC1`/`SC01` numeric-alias reuse, qualified legacy reservation collisions such as `SC01-old`, unclassifiable legacy IDs, free-form Blueprint fields, incomplete V1/V2 semantic data, missing V2 inner intents, and missing audio payloads. |
| SSG-04 | Both closed remove directions reject last Scene, wrong neighbour, stale selection, incomplete survivor payload, gaps, replay, and extra fields; historical revision remains unchanged. |
| SSG-05 | Confirmation is one-shot before locks; cancellation/replay/stale parent/snapshot/epoch/Project all cause no Proposal or Production delta. |
| SSG-06 | Concurrent structure apply versus ordinary revision/GO/finalization, Plan install, Candidate registration, `mark_ready_for_audit`, and `prepare_lock`/`apply_lock` allows one linearized result only; no nested same-lock acquisition, deadlock, partial proof, or silent retry. |
| SSG-07 | Successful structure apply appends exactly one Proposal revision, advances epoch, invalidates GO/finalization/Plan consumers, survives restart readback, and leaves Production Slots/Candidates/Edges byte-for-byte unchanged. |
| SSG-08 | Post-install/nonempty state never migrates, clears, or reinstalls Production; it returns one Japanese recovery action with provider/paid/native/timeline/export effects false. |
| SSG-09 | Bridge rejects unknown/extra fields and only exposes the new typed methods; it does not route structure commands through visual scene revision. |
| SSG-10 | Shell uses status-driven add/remove controls, one handler invocation and canonical readback; it displays only public Scene identity and no direct store access, page-local model selector, raw security data, or universal-enable regression. |
| SSG-11 | Legacy visual coverage is migrated by retaining both the status-driven add/remove disabled regression and the prior Scene-finalization exact prepare/apply/snapshot-binding regression. |
| SSG-12 | A fault after Proposal append but before immediate readback returns only `AMBIGUOUS_AFTER_PROPOSAL_WRITE / RECOVERY_REQUIRED`; no rollback, second append, retry, reused confirmation, or fresh preparation occurs.  While that Project has unresolved matching recovery, status disables every new structure operation.  Restart readback resolves only a matching persisted operation commitment to `APPLIED_EXACT` or a proven no-write outcome. |
| SSG-13 | Epoch is explicit in root/ordinary/structural Proposal revisions and binds finalization/Plan/consumer paths.  Missing legacy epoch, parent/child epoch gap, old Plan epoch, and forged operation commitment all fail closed without migration or Production delta. |

## Implementation entry gate

Source/test implementation may start only after all are true:

1. a cross-owner TASK-027/TASK-037 protocol allocates the exact gate and
   transaction boundary, including lock ownership and no-nesting proof;
2. an independent Critic records `0 Critical / 0 High` against this design and
   any bounded revision;
3. current main, branch/worktree, dirty ownership, overlapping PRs, and exact
   Allowed Files are freshly bound;
4. the focused matrix is assigned across TASK-027, TASK-037, and TASK-036;
5. no Provider, native GUI, paid, Release, Deploy, or Production authority is
   inferred from this task.
