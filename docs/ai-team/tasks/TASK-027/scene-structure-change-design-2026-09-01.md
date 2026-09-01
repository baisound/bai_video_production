# TASK-027 — Scene Structure Change Design

- Date: `2026-09-01`
- Canonical source: `19c37245a1444f6f3ed5f3b707eeea94e68602b0`
- Development profile: `DEV-3 HIGH ASSURANCE`
- Decision: `DESIGN_COMPLETE / IMPLEMENTATION_STOP_CROSS_OWNER_ALLOCATION_REQUIRED`

## Scope and non-effects

This design adds a future, typed Scene-structure operation to TASK-027.  It is
separate from the existing visual-only Scene revision.  It covers only a
pre-install Planning Proposal revision.  It does not create a Provider call,
paid execution, Asset/Candidate, Timeline, Resolve, export, publish, or native
effect.

The future Shell uses the existing central Settings > AI models presentation as
read-only context only.  It does not accept a page-local model selection, a
model route, a provider, or a settings write as part of a Scene operation.
Project identity and currentness are verified through the trusted Project,
Proposal, and Production commitments; they are never supplied as raw paths or
free-form revision values by the user.

## Current-source findings

`Task027PlanningApplication._scene_revision_blueprint` requires the same Scene
count, order, and IDs.  `prepare_scene_revision` and `apply_scene_revision`
therefore remain the correct path for visual/frame edits only and cannot be
expanded into structural edits.

The current Production installer accepts a historical Approved Plan and
replaces the Production graph wholesale.  Planning and Production currently
use separate locks.  Consequently, a check that Production is empty cannot be
made safe by reading a status label before appending a Proposal revision.

`BlueprintSceneV2` requires independently typed start/end `FrameIntent` values
and an audio plan for every Scene.  A shell must not construct these values by
copying a row or infer them from a split frame.

## Typed operation contract

The future Application exposes a separate closed surface:

```text
scene_structure_status
prepare_scene_structure_revision
apply_scene_structure_revision
readback_scene_structure_revision
```

`scene_structure_status` is a public-safe projection.  It distinguishes
`PREINSTALL_EMPTY_READY`, existing Production state, missing/currentness
conflicts, and unavailable cross-store authority with Japanese reasons and one
valid next action.  It never exposes lock paths, raw hashes, or internal
authority labels in the normal UI.

Preparation seals a single Project identity, Proposal snapshot SHA, parent
Proposal SHA/revision, active structure epoch, Production snapshot SHA, and an
exact proof that the Production graph has zero Slots, Candidates, and Edges.
This proof is created by the trusted Application; it cannot be reconstructed
from Shell input.  Preparation produces a preview and a one-shot Human
confirmation only.

The closed operation kinds are:

- `ADD_SPLIT`
- `REMOVE_SELECTED_INTO_PREVIOUS`
- `REMOVE_SELECTED_INTO_NEXT`

All requests reject extra fields.  They carry selected Scene identity and
closed operation data, not a free-form full Blueprint or raw FrameIntent JSON.
The Application performs bounded parsing and typed validation.

### ADD_SPLIT

The existing selected Scene always keeps its ID and becomes the left range
`[old.start, split)`.  A deterministic lowest unused numeric `SC` ID becomes
the right range `[split, old.end)`.  The split is strictly interior, both
children contain at least one frame, the final count is at most 256, and the
whole ledger remains gapless.

Both resulting Scenes supply full, independently validated semantic payloads.
For V2, the new `left.end_frame_intent` and `right.start_frame_intent` are
explicit typed inputs.  Only an unchanged matching outer boundary may carry
forward (`left.start` or `right.end`).  Both audio plans and all narrative,
source, risk, camera, reference, and policy content are explicit; cloning or
inference is forbidden.

### REMOVE_MERGE

Removal is only a merge and requires more than one Scene.  The operation name
unambiguously identifies the surviving neighbour and the deleted selected ID;
both IDs appear in preview and receipt.  The survivor supplies a complete V1
or V2 semantic payload for its resulting range, including both V2 FrameIntents
and audio.  Unaffected Scene IDs remain stable, and the resulting ledger must
remain gapless.

Historical Proposal revisions retain the removed Scene; no historical record is
rewritten or deleted.

## Cross-store linearization gate

Implementation is not authorized by this design alone.  TASK-027 and TASK-037
must first receive a jointly owned, per-Project `SceneStructureGate` protocol.
Every Production graph mutator, including Plan installation, Candidate
registration, and WORLD LOCK mutation, must honor that gate.

The mandatory order is:

```text
SceneStructureGate
  -> TASK-027 Proposal/Application snapshot lock
  -> TASK-037 Production snapshot lock
```

Production-only graph mutations use the gate before the Production lock.  Plan
installation also validates the current TASK-027 active Proposal revision and
structure epoch while the gate is held.  Structure apply takes the fixed order,
rereads the sealed Planning and Production commitments and empty graph proof
under those locks, then appends exactly one new Proposal revision.  It does not
write, clear, migrate, or reinstall the Production graph.

Appending a structural revision atomically advances the active structure epoch
and makes prior GO, Scene finalization, and Approved Plan usability stale.  The
historic Plan remains append-only evidence, but every Production Plan consumer
must require the active Proposal revision and structure epoch.  This replaces
the current historical-plan-only consumer behavior.

Any installed, nonempty, unknown, stale, mismatched, or ambiguous Production
state disables the operation.  There is no automatic migration, reinstall,
cleanup, recomputation, or retry.

## Apply, readback, and recovery

Apply marks the one-shot confirmation consumed before acquiring locks.  It
fails closed if any sealed commitment, Project currentness, structure epoch,
lock order, parent identity, or empty-graph proof has changed.  A failure does
not permit reusing the confirmation; a new status and preparation are required.

On success, the Application returns the new Proposal receipt and a fresh
readback.  The normal UI tells the user that the plan must be reviewed and
confirmed again.  The UI is a continuous frame-ribbon split/merge preview with
Japanese reason and recovery CTA; it does not write stores directly or expose
raw IDs, routes, policies, or security terms.

## Required verification before implementation closure

- clean pre-install split and merge, receipt/readback, and restart recovery;
- V1 and V2 payload validation, including both new V2 inner FrameIntents and
  both audio plans;
- interior/minimum/maximum frame tests, 256-plus-one, gapless ledger, stable
  IDs, and invalid semantic payloads;
- one-shot confirmation, cancellation, stale parent/snapshot/Project/epoch,
  replay, and concurrent apply negatives;
- all race orderings with Plan install, Candidate registration, and WORLD LOCK
  mutation;
- historic Plan rejection after a structural revision;
- exact Shell bridge request rejection and handler-once behavior;
- post-install/nonempty state disabled with an actionable Japanese reason;
- packaged clean-project UI exercise is separate Development 4 evidence and
  remains `NOT_EXECUTED / NOT_CONFIRMED` until observed.

## Independent review

The revised design received an independent Critic result of `0 Critical / 0
High / 0 Medium` and an independent Judge result of `0 Critical / 0 High / 0
Medium / 0 Low` against the canonical source above.  Those decisions do not
grant the cross-owner implementation allocation, Provider execution, native
operation, or Production authority described as blocked here.
