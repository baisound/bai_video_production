# TASK-036 P-UX-2H locked visual Asset edit placement design

Date: `2026-08-21`
Status: `ARCHITECTURE_ESCALATION_PASS / H-A_IMPLEMENTATION_PASS / H-B_H-A_INTEGRATION_GATED / DEV-3 HIGH ASSURANCE`

The initial design exhausted its two ordinary DEV-3 review/fix cycles with two
cross-cutting persistence questions still open. This document therefore does
not authorize a third incremental fix. It replaces the original single unit
with the two bounded units in section 3. H-A must reach an independent
implementation-ready decision before source mutation begins. H-B remains
blocked on H-A reaching a merged or otherwise safely integrated boundary.
Fresh-main coordination confirmed that TASK-026 does not read TASK-044's
interactive Timeline store, so no Audio-domain compatibility change is a
dependency of this unit. A future Audio consumer of that store requires a new
typed read-boundary coordination before implementation.

## 1. Goal

Connect the already canonical visual flow:

```text
TASK-013 completed local generation
  -> TASK-027 verified output adoption
  -> TASK-038 Human ACCEPT
  -> TASK-037 Candidate LOCK
  -> TASK-003 IMAGE Asset
  -> exact insert or replace in TASK-044 Timeline edit history
  -> fresh Edit screen read-back
```

This unit closes the bounded P-UX-2 F6/F7 handoff. It does not run a
Provider, create or accept a Candidate, mint a LOCK, mutate Resolve, render,
Export, publish, release or complete P-UX-2E.

## 2. Canonical ownership

- TASK-003 `SQLiteProductStore` owns the immutable Asset identity, media kind,
  logical URI, checksum and rights projection.
- TASK-037 owns Slot, Candidate, Human ACCEPT/LOCK and STALE truth.
- TASK-044 owns the append-only Timeline edit history and Project child
  binding.
- TASK-036 only compiles the exact cross-owner placement request and exposes it
  through the existing trusted Shell.

No second Asset Registry, Candidate store or Timeline is introduced.

## 3. Escalated Atomic Unit split and source scope

### H-A: TASK-043/TASK-044 reversible placement foundation

H-A owns only persisted grammar, projection and transaction recovery:

- `interactive_timeline_edit.py`
- `interactive_timeline.py` only if the typed source-binding projection belongs
  beside the canonical clip type
- `interactive_timeline_store.py`
- `project_save.py`
- `project_history.py` only for a coordinator-owned locked CAS helper
- public and packaged Project-save/Timeline-edit schema mirrors
- exact TASK-043/TASK-044 tests and this design document

H-A introduces no TASK-036 Shell method, concrete Project-history participant
or UI. Its completion boundary is a backward-compatible v1.1 Timeline history
with reversible source bindings plus a generic, bounded Project-save
participant lifecycle proven with a test participant. It provides the locked
CAS primitive which H-B uses without re-entering the Project lock.

### H-B: TASK-036 visual placement and readiness composition

H-B starts only after H-A is merged or safely integrated. It may modify:

- new `task036_visual_asset_placement.py`
- `interactive_timeline_application.py`
- `final_review_readiness.py`
- `task044_nle_shell.py`
- `task036_shell_ui.py`
- `task036_shell_v611.py`
- `task036_trusted_launcher.py`
- exact exports in `__init__.py` only if required
- exact TASK-036 placement/readiness/Shell/UI tests and this design document

H-B owns the concrete TASK-044 Project-history participant. It removes the
post-COMMITTED history gap for new v1.1 placement operations while retaining a
read-only compatibility path for a pre-existing v1.0 recovery sidecar.

`CHANGELOG.md`, audio-domain source, Provider adapters, Resolve, Export and
release files are outside this Atomic Unit.

## 4. Eligibility contract

A placement candidate is available only when every condition is current:

1. Production Slot belongs to the active Project, has `LOCKED` status and is
   not STALE.
2. Its `locked_candidate_id` selects a `CandidateLifecycle.LOCKED` Candidate
   in the same Slot.
3. Candidate `asset_id` and `asset_sha256` exactly match one TASK-003 Asset.
4. Asset belongs to the configured Product Job and has `AssetType.IMAGE`.
   P-UX-2H accepts only the exact TASK-027 generated-output profile: source
   Project equals the active Project; rights/commercial/derivative/reuse are
   all `UNKNOWN`; retention is `STANDARD`; audio rights are
   `NOT_APPLICABLE`; `human_lock` is false; restrictions are the exact ordered
   tuple `(HUMAN_RIGHTS_REVIEW_REQUIRED, PUBLICATION_NOT_AUTHORIZED)`; and the
   provenance object has exactly the canonical TASK-027 fields with kind
   `TASK013_COMPLETED_LOCAL_GENERATION`, matching execution, queue-entry and
   output hashes, and false replay/paid flags. Unknown or extra restriction or
   provenance fields fail closed. This is a placement-only predicate, not
   rights approval.
   The restrictions and UNKNOWN states remain unchanged after placement and
   downstream publication stays blocked.
5. Target Timeline belongs to the same Project. Target track is a visual
   VIDEO/OVERLAY track. Controller presentation-lock is an in-memory UI aid,
   not canonical eligibility or a persisted authority coordinate; the UI
   refuses preparation while locked, but apply authority is determined only
   by canonical Project/Production/Timeline state.
6. Insert range is positive and contained. Replace preserves the exact target
   clip range and track.

Only logical IDs and checksums cross the Shell. Host paths and image bytes are
never returned to JavaScript.

## 5. TASK-044 edit schema v1.1

Add edit kinds `INSERT_CLIP`, `REMOVE_CLIP` and `REPLACE_CLIP`.

- insert stores `before_clip = null`, `after_clip = exact new clip`;
- remove stores the exact existing clip as `before_clip`, `after_clip = null`;
- replace stores both exact before and after clip snapshots;
- inverse(insert) is remove, inverse(remove) is insert, and inverse(replace)
  swaps the two snapshots;
- projection requires exact clip absence/presence and exact before snapshot;
  drift is a conflict, never a best-effort replacement.

Exact clip construction is deterministic:

- insert `clip_id` is `visual-` plus the full lower-case SHA-256 hex digest of
  canonical `{project_id,candidate_id,asset_id,target_track_id,start,end}`;
- `source_owner = TASK-003`, `source_ref = asset_id`, `source_sha256` is the
  exact Asset checksum, `state = PLACED_LOCKED_ASSET`, and
  `review_candidate_id = candidate_id`;
- label is the literal `scene_id + " / " + slot_kind`. Both inputs use the
  existing ASCII identity/enum bounds, so the result is at most 224 characters
  and never truncates or hashes display text;
- replace preserves the target clip ID, track and frame range and changes only
  the exact source/label/state/review binding;
- insert of the same exact identity conflicts with the existing clip rather
  than minting a second copy.

Backward compatibility is mandatory. The closed grammar is:

- a v1.0 command has exactly these 12 body fields:
  `command_id`, `kind`, `target_clip_id`, `target_track_id`,
  `before_start_frame`, `before_end_frame`, `after_start_frame`,
  `after_end_frame`, `in_frame`, `out_frame`, `track`, `snap`, plus
  `command_sha256`; only the six legacy edit kinds are legal;
- a v1.1 clip command has those fields plus exact `before_clip`, `after_clip`,
  `before_source_binding` and `after_source_binding` fields; only
  INSERT/REMOVE/REPLACE are legal;
- v1.0 revisions retain the existing exact revision fields, literal version,
  serialization and SHA-256;
- v1.1 revisions use the same revision field names with literal version
  `1.1.0`; their command may be a legacy-shape command or a v1.1 clip command;
- revision order is a zero-or-more v1.0 prefix followed by zero-or-more v1.1
  rows. A v1.0 row after the first v1.1 row is an illegal downgrade;
- snapshot v1.0 is legal only when every row is v1.0 (including empty);
  snapshot v1.1 requires at least one v1.1 row;
- after a history first reaches v1.1, every later revision is v1.1 even for a
  legacy trim/move/track/undo/redo command;
- old command/revision/snapshot bytes and SHA-256 remain unchanged;
- the Project child binding version exactly equals the serialized snapshot
  version. The reader accepts 1.0 or 1.1 and writer never downgrades;
- foreign, illegal mixed-prefix, checksum-invalid and unknown-version shapes
  fail closed.

Each non-null v1.1 source binding is body-free and contains Project,
Production snapshot, Scene, Slot, Candidate, Asset, Asset SHA, configured
Product Job, generation execution, queue entry, and the literal
`publication_authorized = false`. It contains no host path or prompt body.

The clip and binding pairs are exact and reversible:

- INSERT is `(before_clip=null, before_binding=null)` to
  `(after_clip=B, after_binding=binding-B)`;
- REMOVE is `(before_clip=B, before_binding=binding-B)` to
  `(after_clip=null, after_binding=null)`;
- REPLACE from an earlier P-UX-2H clip is `(A, binding-A)` to
  `(B, binding-B)`;
- REPLACE from a legacy/base clip is `(A, null)` to `(B, binding-B)`;
- inverse swaps both clip snapshots and both bindings; redo reuses the original
  two pairs with only a fresh command ID;
- projection maintains `(clip, binding-or-null)` state. It requires the active
  pair to equal the command's exact before pair before applying the after pair.
  Existing base clips begin with a null binding. A v1.0-prefix row and a
  legacy-shape command in a v1.1 revision mean `LEGACY_UNCHANGED`: they alter
  only their existing range/track/in-out domain and preserve the active binding
  map. Null is an explicit clip-command side, not an instruction silently
  inferred for legacy commands. A binding is never reconstructed from current
  Production state or borrowed from the other side of a command.

The existing `TimelineEditProjector.apply()` result remains backward
compatible. H-A adds a typed projection which returns the same Timeline/in-out
result plus the active clip-ID to source-binding map. H-B consumes that map for
fresh placement currentness; no second persisted index is created.

## 6. Cross-store linearization

Apply lock order is fixed:

```text
Project Manifest lock
  -> TASK-037 production snapshot lock
  -> validate exact Production snapshot/Candidate/Asset binding
  -> TASK-044 child and Project Manifest commit
```

`ProductProjectSaveCoordinator` gains one narrow optional transaction
participant plus the independent commit guard. Under the Project lock it enters
the commit guard before creating any TASK-043 or TASK-044 recovery file.
P-UX-2H's guard then takes the TASK-037 snapshot lock, reloads exact current
truth and rejects any drift. Only after that succeeds, the coordinator derives
the exact transaction ID and calls the participant's prepare operation.

Before transaction-ID derivation, the optional participant produces an
immutable plan containing its closed participant ID/version, Project ID,
source/target Manifest hashes and participant-specific expected source/target
content hashes. The plan has a canonical binding SHA. The coordinator includes
that binding SHA in the save transaction identity, then supplies the derived
transaction ID back to participant prepare. This avoids a circular hash while
making a save with another participant plan a different operation.

The concrete H-B participant writes one checksum-closed TASK-044 recovery
record containing the transaction ID, binding SHA, Project ID, source/target
Manifest hashes, expected/current Project-history hashes and the exact target
Project history. Prepare returns an exact receipt SHA. Project-save journal
v1.1 stores the immutable plan/binding SHA and prepared receipt SHA before any
child staging.
Journal v1.0 bytes and parser behavior remain unchanged; v1.1 is used only when
a participant is present, and transition serialization never changes a
journal's version or descriptor.

The coordinator keeps the Project/Production guard through child commit,
Manifest commit, participant reconciliation and durable `COMMITTED` journal
state. The participant may use only the coordinator-owned `_save_unlocked`-like
CAS primitive; acquiring the Project lock recursively is forbidden. Successful
reconciliation returns a checksum-closed result receipt bound to participant,
binding SHA, transaction ID, outcome and resulting content SHA. The journal
persists that result before its terminal transition. H-B's COMPLETE result
CAS-writes the exact target Project history and deletes only the exact recovery
transaction/SHA. It is idempotent when the target history already exists. If it
fails after Manifest commit, the journal remains recovery-required/committing
and offers FINALIZE only; it is not marked COMMITTED. Existing callers use the
unchanged v1.0 no-guard/no-participant path.

This order matches generation-output adoption (`Project -> Production`) and
avoids the reverse-lock deadlock. Asset rows are insert-only immutable records;
their exact ID/checksum/job/type/rights are re-read during the same guard.

Guard rejection occurs before either recovery file exists. If participant
prepare succeeds but Project-save journal creation fails, abort runs while the
same Project/Production locks are held and removes only the exact recovery
transaction/SHA it created. A crash in that narrow pre-journal window leaves an
orphan that H-A reconciles under the Project lock: source Manifest means exact
abort; any foreign/ambiguous state fails closed.

Project-save recovery for a v1.1 participant journal requires a runtime
participant with the exact descriptor identity. Calling generic COMPLETE or
ROLLBACK without it, or with another participant, fails closed. Human COMPLETE
first finishes/validates the exact child+Manifest transaction, then finalizes
the Project history under the same Project lock, then persists COMMITTED.
Human ROLLBACK restores the source children, aborts only the exact TASK-044
recovery, then persists ABANDONED. COMPLETE/ROLLBACK return only after the live
application reloads the resulting history/revision; constructor recovery uses
the same idempotent participant logic after restart. Two instances cannot
overwrite or unlink each other's recovery receipt.

The v1.1 journal parser requires the exact participant plan, prepared receipt
and nullable result receipt fields. Unknown participant IDs/versions, changed
binding hashes, transaction identities that do not include the binding, result
receipts for the wrong outcome and terminal journals without a matching result
all fail closed. v1.0 journal transaction IDs and bytes are never recomputed
with the new rule.

The exact TASK044 recovery API, not raw generic TASK043 recovery, is exposed for
participant journals. Its public status reports transaction ID, action and
whether history reconciliation is pending. It never automatically selects
COMPLETE versus ROLLBACK.

Later Production STALE is ordered after an admitted commit and never rewrites
history. A fresh H-B placement projection compares every non-null active source
binding with current Production/Candidate/Asset truth and returns a
checksum-closed placement snapshot. `Task036FinalReviewReadinessProjection`
binds that snapshot hash and emits one `STALE_VISUAL_ASSET_PLACEMENT` blocker
per stale clip. Missing/unavailable placement currentness fails closed whenever
the projected Timeline contains a non-null placement binding. This keeps a
re-locked Slot from making an older placed Candidate appear current. Human
ROLLBACK creates no committed Timeline revision or Project-history record. No
guard failure is projected as a committed edit.

## 7. Human confirmation and recovery

Prepare returns one body-free confirmation with operation, Scene/Slot,
Candidate/Asset/SHA, target track/range and exact expected snapshot hashes.
There is one TASK-044-owned pending confirmation, not nested TASK-036/TASK-044
tokens. The P-UX-2H facade returns that identity unchanged. TASK-044 protects
token reservation/pop with one in-process lock, enforces a 256 cap, and offers
exact cancel. Apply and cancel atomically race for the same pop; exactly one
wins. Prepare failure rolls back no second reservation.

Restart loses uncommitted confirmations safely. A committed TASK-044 revision
is canonical and read back through the existing Timeline projection. Project
save interruption uses existing TASK-043 recovery; no automatic replay occurs.

Undo/redo rules are exact:

- undo INSERT applies its exact REMOVE inverse; undo REMOVE applies exact
  INSERT; undo REPLACE swaps exact before/after snapshots;
- redo reconstructs the original exact before/after binding pairs with a new
  command ID and requires the current projected clip/binding absence or exact
  before-pair precondition;
- APPLY or REDO that inserts/replaces a P-UX-2H source re-enters the same
  Project/Production/Asset commit guard. If the source is now STALE or rights
  drifted, redo fails with no revision;
- an UNDO compensation that removes or restores an earlier snapshot does not
  mint fresh placement authority and needs only exact Timeline/Project CAS;
- these rules are identical after restart and in a v1.0-prefix/v1.1 history.

## 8. Shell and UI

The trusted launcher binds P-UX-2H only when the Product Manifest, TASK-003
store/Job, TASK-037 and TASK-044 mutation composition are available under the
existing runtime lease.

Public bridge methods:

- `visual_asset_placement_snapshot`
- `visual_asset_placement_prepare_insert`
- `visual_asset_placement_prepare_replace`
- `visual_asset_placement_apply`
- `visual_asset_placement_cancel`

All calls are guarded for the full operation by the existing NLE runtime lease.
The Assets page exposes Insert only for eligible LOCKED IMAGE rows. Replace is
shown only when the current Edit selection identifies one exact visual clip.
The confirmation dialog shows only logical IDs, frame range and SHA-256. Apply
refreshes both Assets and Edit projection.

## 9. Required verification

Focused positive and negative evidence must include:

- old v1.0 snapshot byte/hash compatibility and v1.0 -> v1.1 upgrade;
- insert/replace/remove projection plus binding-pair undo/redo and restart
  read-back, including legacy A -> generated B -> undo and generated A ->
  generated B -> undo;
- duplicate clip, wrong before clip, range/track/media mismatch;
- non-LOCKED/STALE/foreign Candidate, Asset ID/SHA/job/type/rights mismatch;
- Project/Production/Timeline drift at prepare and apply;
- barrier drift while the Project lock is held: provider 0 and no Timeline
  revision;
- confirmation single-use, cancel, capacity and apply/cancel race;
- Project-save journal v1.0 byte/hash compatibility and participant-only v1.1;
- participant prepare failure, pre-journal crash/orphan cleanup, normal finalize,
  after-Manifest FINALIZE, COMPLETE, ROLLBACK, tamper and wrong-participant
  failures with exact live-runtime and restart read-back;
- two-instance barriers proving one recovery receipt cannot be overwritten or
  deleted by another transaction;
- placement currentness and Final Review blocker when a formerly placed
  Candidate/Slot becomes stale or is replaced by a newly LOCKED Candidate;
- old bridge after launcher close and in-flight close barrier;
- bound Shell/UI Insert and Replace vertical with fresh Timeline read-back;
- no Provider, paid/cloud, Candidate ACCEPT/LOCK, Resolve, Export or
  publication effect.

After focused tests, run impacted TASK-003/037/043/044/TASK-036 Shell and
trusted-launcher regression, Python compile, embedded JavaScript contract tests
and `git diff --check`. Full regression is required before PR readiness because
this changes a canonical persisted Timeline schema.

## 10. Completion boundary

P-UX-2H is complete when an already Human-LOCKED generated IMAGE Asset can be
inserted or replace one selected visual clip, survives restart as one exact
TASK-044 revision, and is projected on the Edit screen with the same Asset
identity and checksum.

This does not claim the complete application flow. Audio completion remains a
consume-only dependency from the Development audio lane, and real packaged
Windows model-to-export read-back remains P-UX-2E.
