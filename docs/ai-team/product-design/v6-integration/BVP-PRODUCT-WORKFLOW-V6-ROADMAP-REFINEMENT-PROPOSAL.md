# BAI VIDEO PRODUCTION — V6 Product Workflow Roadmap Refinement Proposal Ver.1.0

- Date: 2026-08-14
- Status: `PROPOSAL / OWNER_REVIEW_REQUIRED / NO_TASK_AUTHORIZATION`
- Snapshot baseline:
  - stable release `v0.20.1`
  - R2 Production Control promotion complete
  - R3 Continuity / Prompt control promotion complete
  - R4 local adapter + safe-readiness hosted closure complete
  - native H3 parked
  - no active Consumer Task
  - next recorded decision = TASK-013 safe native-runtime resumption

---

# 1. Proposed roadmap change

Insert a cross-cutting **V6 Product Workflow Reconciliation and Integration** route before TASK-013 Native H3 resumption.

Reason:

The current local generation runtime is intentionally parked. Meanwhile the real production/UI work has exposed required changes to the contracts that will govern the inputs and outputs of future generation:

- frame-specific reference binding;
- iterative World Lock;
- Visual Prompt Director;
- prompt compilation/translation;
- Timeline audio;
- expert quick generation;
- expanded Unified Shell;
- export queue.

It is safer to finalize these contracts while native generation remains parked than to resume execution under a soon-to-be-migrated contract.

---

# 2. Proposed consolidated order

```text
CURRENT
v0.20.1 + R2 + R3 + R4 hosted closure
TASK-013 Native H3 parked
        |
        v
P-V6-0 Current-main Reconciliation / Full Design
        |
        v
P-V6-1 Versioned Blueprint / Frame Binding Migration
        |
        v
P-V6-2 World Lock / Scene-Compatible Reference Integration
        |
        v
P-V6-3 Visual Prompt / Generation / Expert Control
        |
        v
P-V6-4 Timeline Audio / Narration / BGM / SE / Ambience
        |
        v
P-V6-5 Unified Desktop / NLE / Export Queue
        |
        v
P-V6-6 Native UX / Regression Closure
        |
        v
Owner re-evaluates TASK-013 Native H3 resume
```

`P-V6-*` are roadmap slices, not canonical Task IDs.

---

# 3. Task allocation proposal

The next detailed-design team must choose the exact Task architecture.

Recommended bias:

- create a new cross-cutting Product Integration Task rather than reopening completed TASK-036..040;
- reuse completed subsystem contracts;
- revise/evolve their current schemas through the new authorized Task;
- decide whether TASK-041 remains the Audio-specific implementation owner;
- keep TASK-013 Native execution resume separately gated.

Do not assign `TASK-042` or any number solely from this proposal.

---

# 4. Why completed tasks should not be reopened by default

TASK-036..040 have historical Evidence proving bounded completion.

V6 does not invalidate that historical completion.

It introduces a new Product requirement set.

Correct history:

```text
Old bounded contract completed
→ new requirement discovered
→ new migration/integration task
```

Incorrect history:

```text
Old task was secretly incomplete
→ rewrite old completion
```

---

# 5. Dependencies

## Before P-V6-1
- live-main audit
- roadmap/current-state reconciliation
- exact schema inventory
- current tests
- current native state
- full design

## P-V6-1 blocks
- frame-level Lock UI
- Prompt compilation bindings
- accurate STALE propagation
- correct Quick adoption

## P-V6-2 blocks
- reliable Start/End generation UX
- scene-compatible reference generation

## P-V6-3 blocks
- production-ready Quick Generate
- native generation resume under final prompt contract

## P-V6-4 blocks
- complete AI rough timeline for generated productions

## P-V6-5 blocks
- full user-facing V6 Product acceptance

---

# 6. TASK-041 decision

TASK-041 is currently proposed/not authorized.

The design team should explicitly decide one of:

A. expand TASK-041 to own Project Timeline audio semantics and implementation;

B. let a V6 integration Task own the new Timeline contracts, and TASK-041 own only Audio Workspace/placement implementation;

C. replace the current proposed TASK-041 design with a new approved audio boundary.

Do not let two separate Tasks create competing Audio timing models.

---

# 7. TASK-013 native resumption

V6 design work itself does not cancel TASK-013.

It changes the preferred timing.

Native H3 should remain parked until the Owner confirms:

- new reference binding is accepted;
- prompt version/compilation path is stable enough;
- generation authority is unambiguous;
- Candidate/Audit/Lock binding is ready for real outputs;
- safe runtime conditions remain satisfied.

---

# 8. Release strategy

Do not preselect a release version.

Possible strategy after detailed design:

- multiple no-release roadmap checkpoints for Domain/control slices;
- one Product integration candidate after V6 Native UX closure;
- exact semver chosen from actual API/schema/UI impact at release decision.

Blueprint schema compatibility may justify more than a patch release; decide from the actual public/serialized compatibility contract.

---

# 9. Roadmap acceptance criteria

Before changing canonical roadmap:

- current main independently verified;
- all related Task statuses verified;
- all existing implementation surfaces mapped;
- gap register complete;
- exact task split approved;
- migration strategy approved;
- Native H3 dependency order approved;
- no duplicate lifecycle/registry created;
- no historical Evidence rewritten.

---

# 10. Recommendation

Adopt the V6 reconciliation route now, while TASK-013 Native H3 remains safely parked.

Begin with detailed design, not implementation.
