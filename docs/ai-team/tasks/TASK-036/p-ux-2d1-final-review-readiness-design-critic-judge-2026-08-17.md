# TASK-036 P-UX-2D1 Final Review Readiness

Date: 2026-08-17  
Atomic unit: `P-UX-2D1_FINAL_REVIEW_READINESS_R0`

## Boundary and design

The V6.1.1 Final Review page previously recomputed only Production and Audit
counts in JavaScript.  It could not prove that the displayed blockers belonged
to the current Visual handoff and edited Timeline, did not inspect the durable
Export queue, and did not serialize the missing privacy, rights/license,
resource, edit-persistence or delegated Audio completion gates.

`Task036FinalReviewReadinessProjection` is a deterministic, read-only
composition over exact current Product snapshots:

- TASK-037 Production Control snapshot;
- TASK-038 Audit snapshot bound to that Production snapshot;
- P-UX-2C1 Visual Generation Handoff bound to the same Production snapshot;
- TASK-044 projected Timeline and Project Manifest coordinates;
- TASK-044 Export queue rows; and
- a closed set of five external gate receipts: `AUDIO_COMPLETION`,
  `EDIT_PERSISTENCE`, `PRIVACY`, `RESOURCE`, and `RIGHTS_LICENSE`.

The external receipt set is exact and scoped to the same Project and Timeline.
Missing, FAIL, UNKNOWN, STALE or REVOKED entries remain blockers.  Audio is
owned by Developer2; this unit can consume a future exact receipt but contains
no Audio implementation or mutation.

The closed readiness states are `BLOCKED_PRODUCT_GATES`,
`BLOCKED_EXTERNAL_GATES`, and `READY_FOR_TYPED_FINAL_REVIEW`.  The last state
is only an input candidate for a future typed Human Final Review service.  It
does not create an approval, Export Job, render, publication or Human authority.
When any bound Shell source is unavailable, the bridge returns
`SOURCE_UNAVAILABLE` and the exact missing source names.

## Invariants and caps

- Production slots: at most 256; duplicate IDs reject.
- Audit candidates: at most 1,024; duplicate IDs reject.
- Export rows: at most 256; duplicate IDs reject.
- External gate receipts: exact closed universe of five; cap 5, cap+1 rejects.
- All SHA values use canonical `sha256:` plus 64 lower-case hexadecimal bytes.
- Cross-Project, cross-Production or cross-Timeline borrowing rejects.
- A required Production Slot is complete only at exact `LOCKED`; STALE always
  blocks.
- Audit recovery, pending Human actions and critical violations remain separate
  blockers.
- A Project Manifest coordinate is mandatory for the current edited Timeline.
- Any pre-existing unscoped Export row blocks readiness; it cannot be silently
  attributed to the current Final Review.
- Canonical JSON and projection SHA are deterministic.

## Critic

### Builder / Completeness

Finding: accepting all LOCKED Slots alone would repeat the old aggregate's
completion inflation and omit Edit, Visual and Export lineage.  Correction:
the projection binds all five current Product sources, checks their coordinate
equalities and records every product blocker.  Empty required Slot sets and
unbound Project Manifests fail closed.

### Security / Authority

Finding: a generic PASS flag could manufacture privacy, rights or Audio
authority.  Correction: the external registry is a fixed exact set whose rows
must bind Project, Timeline and immutable receipt SHA.  Missing and UNKNOWN are
not inferred.  The output explicitly fixes approval/export/render/publication
and Human authority to false.

### Operations / Compatibility

Finding: an existing Export Job could belong to a different approval epoch.
The current TASK-044 shell rows do not expose a Final Review coordinate.
Correction: every existing row blocks as `UNSCOPED_EXPORT_JOB_PRESENT`; a later
unit must add typed queue creation/binding rather than borrow it.  The Shell
only renders the projection and keeps the approval control disabled.

Residual C/H/M: `0/0/0`.

## Verification and Judge

Required checks:

- deterministic PASS-candidate projection with all exact receipts;
- every missing/product/external/stale/revoked/UNKNOWN branch;
- project, Production and Timeline cross-scope rejection;
- duplicate and cap+1 rejection;
- no filesystem, process, runner or network surface;
- bridge unavailable-source and missing-external-gate behavior;
- V6.1.1 embedded JavaScript and visual contract;
- focused TASK-036 and full repository regression;
- `git diff --check` and exact changed-path inventory.

Independent Judge predicate:

`PASS` only when all checks pass, changed paths remain the authorized exact set,
and no approval/export/render/Audio/Provider/Native H3/Release/Deploy effect is
introduced.  Provisional decision after implementation review:
`PASS_READ_ONLY_FOUNDATION`, Residual C/H/M `0/0/0`.

## Next boundary

P-UX-2D2 may define the typed Human Final Review application and exact receipt
only after all five external owner receipts exist.  P-UX-2D3 may then bind that
receipt to TASK-044 queue creation, per-job dispatch, Render QA and artifact
read-back.  Neither authority is granted by this unit.
