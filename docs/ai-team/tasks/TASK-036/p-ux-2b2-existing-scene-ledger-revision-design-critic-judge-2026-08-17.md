# TASK-036 P-UX-2B2 Existing Scene Ledger Revision

Date: 2026-08-17
Authority: `OWNER-AUTH-20260817-DEVELOPER1-EXCLUSIVE-ROADMAP-QUEUE-AUTONOMY-01`
Checkpoint base: `cfe89ce774c783a2bbc6840ba471a1fd48f4e48a`
State: `IMPLEMENTED_NO_PROVIDER_EFFECT / REVIEW_CANDIDATE`

## Scope

This unit connects revision of existing TASK-027 Blueprint Scene rows to the
TASK-036 Scenes page. It accepts exactly one ordered row for each existing Scene
and may change only its frame range and visual planning fields. It preserves the
Scene identity, references, Audio plan and v2 Start/End FrameIntent values, plus
the Proposal Intent, sections, Provider Policy, cost, currency and rights.

Scene add/remove, Timeline finalization, media access, detector/provider work,
generation and Resolve remain separate. Audio and TASK-041 remain owned by
Developer2.

## Contract and lifecycle

1. `prepare_scene_revision` binds the exact persisted snapshot, parent Proposal
   hash and 1..256 existing Scene rows.
2. Scene order, IDs and cardinality must equal the current Blueprint. The input
   surface excludes references, Audio and v2 FrameIntent fields.
3. Existing R0 Blueprint constructors revalidate unique IDs, exact gapless frame
   coverage, target duration, enum values and dense-UI safety; duplicate range
   validation is not introduced.
4. The candidate is Proposal revision `n+1`; its confirmation is one-shot.
   `apply_scene_revision` rechecks the snapshot/parent under the Product-local
   lock and persists through the existing CAS store.
5. A prior Approved Plan remains immutable history. The changed Proposal needs a
   fresh Human GO before any downstream installation.

The Shell enables only `Scene更新`. Add, remove and Timeline finalization remain
disabled with explicit reasons. The UI submits no Audio/reference/FrameIntent or
execution fields.

## Verification

- v1 append/reopen and preservation of references/Audio/Proposal authority data;
- v2 preservation of both FrameIntent values and Audio;
- fresh GO requirement after an already approved revision;
- no-op, order/cardinality/field drift, gap/overlap and bool-frame rejection;
- concurrent writers permit exactly one CAS publication;
- exact Shell bridge envelope and one-shot confirmation;
- deterministic element inventory update and no-effect Scene UI contract;
- focused/adjacent/full regression, embedded JavaScript syntax and diff check.

## Builder / Completeness Critic

Finding: a broad Scene editor could accidentally fork reference, Audio or v2
frame-intent truth. Resolution: those values are absent from the accepted input
and copied from each exact existing Scene. Existing Blueprint constructors own
all ledger invariants. Residual C/H/M: `0 / 0 / 0`.

## Security / Authority Critic

Finding: revising a Blueprint after GO could be mistaken for approval or start
Provider/NLE work. Resolution: the new Proposal always needs fresh GO, all effect
flags remain false, and the API surface accepts no path, bytes, callback, runner,
provider or execution coordinate. Residual C/H/M: `0 / 0 / 0`.

## Operations / Compatibility Critic

Finding: stale Shells or mixed v1/v2 Projects could lose data or publish twice.
Resolution: version-specific reconstruction preserves opaque constituent values,
while snapshot/parent checks, one-shot tokens, an exclusive lock and CAS reject
stale/duplicate publication. Existing snapshots need no migration. Residual
C/H/M: `0 / 0 / 0`.

## Independent Judge

`PASS_NO_PROVIDER_EFFECT_PUX2B2_PROVISIONAL`

The implementation is admissible for hosted review after exact changed-file
review and all local/hosted checks pass. This Judge grants no Scene add/remove,
Timeline finalization, Human GO, Provider, media, Audio, Resolve, Release, Deploy
or Production authority.
