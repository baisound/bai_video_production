# TASK-042 — P-V6-2 AUTONOMY, Current-main Audit and Builder Design

## Source of Truth and AUTONOMY decision

- Product Authority: `BAI VIDEO PRODUCTION`
- Fresh baseline: `f5ad4cdfa564285e9fe7a5fcf4516f1b92cae0a4`
- Closure Sync PR: `#54`, all `9 / 9 PASS`
- Closure Sync exact head: `89ce567503b22a5e851ad66407e0a57598e79d05`
- Remote Closure Sync branch and dedicated clone: removed
- Handoff Bootstrap: `HANDOFF_STALE`; current clean main is Source of Truth
- Bootstrap checksum: `sha256:bdafc68f8017f87ace6aca18daac0f1de5a82120c0364308ef07e157d4c87b54`
- Bootstrap manifest checksum: `sha256:6d0706ddce366bf82f99390a421aed006810f35e2ab1939ae4e42c7c77c72356`
- Autonomous Queue result: `RUNNABLE_TASK_SELECTED`
- Selected: `BVP-TASK-042-P-V6-2-DESIGN / DESIGN_ONLY`
- Queue checksum: `sha256:3308c13fe176ee8b3a590912f73f26aaa75a4656786f40a9c63ec1061dc7c063`
- TASK-013 Native H3: `PARKED / HUMAN_GATE_REQUIRED / NO_REPLAY`
- OS TASK-017: `PARKED / AUTONOMY_TASK_NOT_AUTHORIZED`
- System blocked: `false`

AUTONOMY governs development selection only. It does not grant BVP runtime,
Provider, paid, native, credential, release, deploy or Production authority.
This P-V6-2 branch is design-only. Product source implementation must wait for
this design PR to pass hosted checks, merge to main and complete branch/clone
cleanup.

## Current-main audit

### Reusable canonical foundations

1. `ProductionBlueprintV2` already stores exact ordered START/END Character,
   Space and Composition bindings containing Slot, Candidate, Asset and checksum
   identity. It does not duplicate lifecycle state.
2. P-V6-1B Human GO verifies every deterministic frame path and exact Asset
   identity. `ApprovedProductionPlan` binds the immutable Blueprint checksum,
   but correctly does not claim that the referenced Candidate is still locked.
3. TASK-037 is the only canonical owner of `SceneAssetSlot`, `AssetCandidate`,
   Human official `LOCKED`, and transitive `STALE` propagation.
4. TASK-038 is the only Human ACCEPT/REJECT decision owner. AI audit content
   cannot lock or reject a Candidate.
5. TASK-039 already enforces non-overridable exact Asset ID/checksum for
   `DIRECT_CONTINUATION`, persists its resolution and binds continuity edges
   into TASK-037 stale propagation.
6. Production, Proposal, Audit, Continuity, Prompt and Queue stores already use
   bounded parsing, checksummed snapshots, atomic replace and exact CAS/recovery
   boundaries. P-V6-2 must reuse them and add no WORLD LOCK store.
7. Generation Queue already compares all upstream snapshot identities and
   requires LOCKED/CURRENT Slot input proofs, but it also accepts a Human-GO
   Asset reference alone. That v1 behavior must remain compatible; v2 must
   require the stronger exact Slot/Candidate proof.

### Exact gaps

1. `SlotKind` lacks the additive reference roles `CHARACTER_REFERENCE`,
   `SPACE_REFERENCE` and `COMPOSITION_REFERENCE` required by the V6 design.
2. `ApprovedPlanProductionControlInstaller` intentionally rejects v2 with
   `ERR_BLUEPRINT_V2_PRODUCTION_CONTROL_NOT_INTEGRATED` and therefore cannot
   project a v2 Scene into existing Production Control.
3. No service verifies that every v2 binding still resolves to the exact
   project-scoped Slot, its official locked Candidate, exact Asset ID/checksum,
   and `LOCKED/CURRENT` state at production-use time.
4. Planning treats any pre-existing reference Slot as
   `OTHER_PRODUCTION_STATE`; a valid WORLD LOCK foundation cannot currently
   precede v2 Plan installation.
5. Approved Plan trace validation compiles only v1 and cannot prove the v2
   frame-binding dependency edges used for stale propagation.
6. Queue proof derivation sees Human GO and locked Candidates as independent
   hash matches. For v2 it must bind the deterministic frame path to the exact
   Slot/Candidate named by the immutable Blueprint, not choose by hash alone.
7. Restart recovery can load each canonical store, but there is no deterministic
   cross-store v2 WORLD LOCK projection that reports exact blockers without
   mutating or inventing state.

## DEV Profile re-decision

- Profile: `DEV-4 FOUNDATION CRITICAL`
- Reason: this slice changes cross-store authorization and stale-propagation
  semantics used before expensive generation, while preserving v1 history and
  multiple completed TASK ownership boundaries.
- Required process: current-main audit, exact Allowed Files, Builder design,
  two Critic cycles, focused compatibility/security/recovery tests, full
  regression, hosted checks and exact main verification.

## Builder design

### 1. Additive reference Slot roles

Extend the existing `SlotKind` enum only with:

- `CHARACTER_REFERENCE`
- `SPACE_REFERENCE`
- `COMPOSITION_REFERENCE`

Old snapshots remain byte/behavior compatible. Unknown values still fail
closed. The roles describe Slot purpose only; they do not add another lock flag,
Candidate registry, media store or delete authority.

### 2. Deterministic WORLD LOCK projection

Add `blueprint_v2_world_lock.py` as a stateless integration service over the
immutable Blueprint/Approved Plan and a current TASK-037 registry.

For every deterministic frame path
`{scene}:{START|END}:{CHARACTER:index|SPACE|COMPOSITION}`, derive one row with:

- expected role and `SlotKind`;
- exact Slot/Candidate/Asset/checksum from Blueprint v2;
- matching Human-GO `reference_id`, Asset and checksum;
- current Slot status/revision/stale state;
- current locked Candidate lifecycle and Asset identity;
- `LOCKED_CURRENT` or a stable fail-closed blocker code.

The service rejects missing, extra, duplicated or mismatched GO paths; wrong
project scope or role; missing Slot/Candidate; different locked Candidate;
Asset/checksum drift; and any STALE/non-LOCKED state. It creates no state and
starts no execution. Re-running after restart produces the same checksum-bound
projection from current canonical stores.

### 3. V2 Production Control installation

Widen the existing compiler/installer to the exact v1/v2 union while preserving
v1 output. For v2:

1. verify the immutable Approved Plan;
2. require current WORLD LOCK projection PASS against the exact pre-install
   Production snapshot;
3. compile the existing Scene output Slots and Plan -> Scene -> Slot edges;
4. add deterministic Candidate -> Scene dependency edges for every distinct
   frame binding so existing TASK-037 propagation makes downstream output Slots
   STALE when a referenced lock becomes stale;
5. add the Human Approved Plan -> Scene edges exactly as v1 does;
6. preflight on an isolated registry copy and publish only through the existing
   CAS store, preventing partial authoritative mutation.

Reference Slots are not re-created by Plan installation. Existing reference
Slots are valid pre-install state only when all of them are project-scoped,
role-correct and exact `LOCKED/CURRENT` bindings required by that v2 Blueprint.
Unrelated pre-existing production state remains blocked.

### 4. Planning, trace and restart behavior

- Planning preparation loads the exact current Production snapshot and includes
  the read-only WORLD LOCK projection in its confirmation/report.
- Apply remains one-shot and binds Proposal plus Production snapshot checksums;
  any changed lock consumes and invalidates the prepared confirmation.
- Trace validation supports v1 unchanged and, for v2, proves output Slots,
  Approved Plan/Blueprint Scene edges, exact Candidate -> Scene binding edges and
  a current WORLD LOCK projection.
- Projection output reports `recovery_required` on upstream inconsistency; it
  never silently repairs Proposal, Production, Audit, Continuity or Queue state.

### 5. Generation and continuity admission

- `ApprovedPlanGenerationAdmissionService` accepts v2 only after exact current
  WORLD LOCK verification and automatically includes all bound reference Slot
  IDs in required locked inputs. A caller cannot omit a required v2 Slot.
- Generation Queue keeps existing v1 Human-GO behavior. For v2, each Prompt
  input must resolve through the deterministic frame path to the exact
  `LOCKED_CURRENT_CANDIDATE`; GO-only proof is insufficient.
- Repeated hashes across distinct frame paths remain ambiguous and fail closed
  until P-V6-3 supplies typed Prompt input roles.
- Non-CUT Queue admission continues to require TASK-039 generation-safe
  Continuity Evidence. `DIRECT_CONTINUATION` still requires exact previous-End
  Asset ID/checksum and cannot be Human-overridden.

## Implementation order

1. reference Slot enum/store backward-compatibility tests;
2. pure WORLD LOCK projection and blocker tests;
3. v2 compiler/installer and isolated preflight;
4. Planning prepare/apply and trace/restart integration;
5. v2 Approved Plan generation admission and Queue proof integration;
6. DIRECT/stale/cross-store recovery regression;
7. documentation/status sync, focused/full regression and Critic closure.

## Permanent boundaries

- no second Candidate/LOCK/STALE, Audit, Continuity, Prompt or Asset registry;
- no Provider call, local generation, paid execution, credential use or media write;
- no automatic Human ACCEPT, official Lock, regeneration or repair;
- no native Resolve/Cubase/ComfyUI operation and no replay of Native H3;
- no version selection, Tag, Release, Deploy or Production Activation;
- no P-V6-3 Prompt/Quick Generate implementation in this slice.
