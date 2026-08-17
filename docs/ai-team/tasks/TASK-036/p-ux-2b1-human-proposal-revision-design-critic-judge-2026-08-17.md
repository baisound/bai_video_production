# TASK-036 P-UX-2B1 Human Proposal Revision

Date: 2026-08-17
Authority: `OWNER-AUTH-20260817-DEVELOPER1-EXCLUSIVE-ROADMAP-QUEUE-AUTONOMY-01`
Checkpoint base: `d99d0bc038a16dd03d14ef1489570f9ba46f8645`
State: `IMPLEMENTED_NO_PROVIDER_EFFECT / REVIEW_CANDIDATE`

## Scope

This unit connects the existing TASK-027 append-only Production Proposal model
to the TASK-036 Planning page. A Human can revise only the title/body of the
existing ordered sections and then confirm the exact candidate once. The
revision keeps the canonical Creation Intent, Blueprint, Provider Policy, cost,
currency and rights warnings unchanged.

It does not generate a Proposal, call a Provider, reserve a budget, approve GO,
install an Approved Plan, mutate Production Control/Timeline/Resolve or publish.
Audio and TASK-041 remain owned by Developer2.

## Contract and lifecycle

1. `prepare_revision` binds an exact persisted snapshot, current parent Proposal
   hash and an ordered section set of 1..64 rows.
2. Section IDs, kinds and order must equal the latest Proposal. At least one
   title/body must change; extra fields and cap+1 fail closed.
3. The candidate is revision `n+1` with the exact parent hash. The confirmation
   is one-shot and has no Provider or NLE authority.
4. `apply_revision` takes the Product-local application lock, rechecks the
   snapshot and parent, appends the revision through the existing registry and
   persists it by CAS.
5. Any previously approved plan remains immutable Evidence but does not approve
   the new revision. The Planning projection returns `GO_REQUIRED` and
   `new_go_required_after_revision=true` where applicable.

The Shell bridge accepts only the exact section envelope. The page uses DOM
construction and the existing bridge; prompt cancellation changes nothing.

## Verification

- append/reopen and exact inherited contract equality;
- approved revision -> new revision -> fresh GO required;
- deterministic changed-section projection;
- no-op, reordered/changed identity, extra-field and 65-row rejection;
- concurrent writers permit exactly one CAS publication;
- confirmation reuse rejection;
- exact Shell bridge request and no-effect UI text;
- focused TASK-027/TASK-036, adjacent planning regression, proportional full
  repository regression, JavaScript syntax and `git diff --check`.

## Builder / Completeness Critic

Finding: allowing the UI to rewrite the Blueprint/policy/cost would fork the
TASK-027 source of truth. Resolution: only existing section title/body values
are accepted, while every other Proposal coordinate is copied from the exact
latest parent. Residual C/H/M: `0 / 0 / 0`.

## Security / Authority Critic

Finding: a saved revision could be mistaken for GO or Provider execution.
Resolution: preparation/application both report effect flags false; a revision
always requires an exact fresh GO and cannot call execution or filesystem APIs
other than the existing bounded Project snapshot store. Residual C/H/M:
`0 / 0 / 0`.

## Operations / Compatibility Critic

Finding: two Shells could revise the same parent or stale confirmation state
could be replayed. Resolution: exact snapshot/parent binding, Product-local lock,
CAS persistence and one-shot confirmation reject stale/duplicate publication.
Existing revision 1 snapshots need no migration. Residual C/H/M: `0 / 0 / 0`.

## Independent Judge

`PASS_NO_PROVIDER_EFFECT_PUX2B1_PROVISIONAL`

The implementation is admissible for hosted review after focused/full tests,
exact changed-file review and hosted checks pass. This Judge grants no Provider,
paid, media, Human GO, Production installation, Timeline, Resolve, Release,
Deploy or Production authority.
