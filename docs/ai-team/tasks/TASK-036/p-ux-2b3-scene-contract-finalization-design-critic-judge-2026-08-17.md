# TASK-036 P-UX-2B3 Scene Contract Finalization

Date: 2026-08-17
Authority: `OWNER-AUTH-20260817-DEVELOPER1-EXCLUSIVE-ROADMAP-QUEUE-AUTONOMY-01`
Checkpoint base: `b58096f7bed92148496f142a041191ffc794efa2`
State: `IMPLEMENTED_NO_PROVIDER_EFFECT / REVIEW_CANDIDATE`

## Scope

This unit connects Human finalization of the current GO-approved TASK-027 Scene
ledger to the TASK-036 Scenes page. It creates an append-only receipt that binds
the exact Approved Plan, Proposal revision and hash, Blueprint identity and hash,
and canonical ordered Scene-ledger hash. It does not create another Blueprint or
Scene store.

Scene add/remove, media access, detector/provider execution, generation, Audio,
Timeline mutation, Resolve and publication remain separate. Audio and TASK-041
remain owned by Developer2.

## Contract and lifecycle

1. `prepare_scene_finalization` requires exact current Proposal and finalization
   snapshot hashes, one current Approved Plan, a bounded Human actor identity and
   a not-yet-finalized Proposal revision.
2. The prepared immutable receipt binds the exact Plan, Proposal, Blueprint and
   ordered Scene ledger. Its own canonical checksum is computed before Human
   confirmation.
3. `apply_scene_finalization` consumes the confirmation once, rechecks both
   snapshots and all current Plan/Proposal/Blueprint bindings under the existing
   Product-local lock, and atomically publishes the receipt store.
4. Proposal or Scene revision preserves historical receipts but makes the current
   projection `GO_REQUIRED`. After a fresh GO, the new revision becomes
   `READY_TO_FINALIZE`; historical receipts never authorize the new revision.
5. The Shell enables finalization only from that exact current projection and
   refreshes canonical state after apply. No JavaScript success state is durable.

The bounded receipt store permits at most 256 unique Proposal revision receipts,
rejects duplicate finalization/Proposal hashes, validates every identity and
checksum, rejects symlinks and files over 4 MiB, and treats malformed or tampered
bytes as data-integrity failure.

## Verification

- GO-required, ready, finalized, stale-history and re-finalized lifecycle;
- exact Plan/Proposal/Blueprint/Scene-ledger receipt binding and restart readback;
- one-shot confirmation, duplicate receipt, stale snapshot and concurrent writer
  rejection;
- invalid Human actor and tampered receipt/snapshot rejection;
- exact Shell bridge envelopes and current-projection button gating;
- deterministic element inventory and no provider/media/Timeline effect surface;
- focused/adjacent/full regression, Python/embedded JavaScript syntax and diff
  checks.

## Builder / Completeness Critic

Finding: a second Scene truth store or digest-only finalization could diverge from
the approved Blueprint. Resolution: the store contains receipts only; each row
directly binds the current Approved Plan and complete canonical Proposal,
Blueprint and ordered Scene-ledger hashes. Fresh snapshots are re-derived before
publication. Residual C/H/M: `0 / 0 / 0`.

## Security / Authority Critic

Finding: a historical receipt or UI click could be mistaken for current Human GO
or Provider/NLE authority. Resolution: only the exact current Proposal receipt is
`FINALIZED`; revisions require a new GO and receipt, actor text is bounded, the
bridge has a closed envelope, and every effect flag remains false. Residual C/H/M:
`0 / 0 / 0`.

## Operations / Compatibility Critic

Finding: concurrent windows, restarts or corrupt receipt bytes could publish a
duplicate or hide stale state. Resolution: one-shot tokens, two snapshot checks,
the Product-local lock, atomic replace, bounded validation and append-only
historical projection fail closed without migrating existing Projects. Residual
C/H/M: `0 / 0 / 0`.

## Independent Judge

`PASS_NO_PROVIDER_EFFECT_PUX2B3_PROVISIONAL`

The implementation is admissible for hosted review after exact changed-file
review and all local/hosted checks pass. This Judge grants no Scene add/remove,
Human GO, media/detector/provider execution, Audio, Timeline/Resolve mutation,
Release, Deploy or Production authority.
