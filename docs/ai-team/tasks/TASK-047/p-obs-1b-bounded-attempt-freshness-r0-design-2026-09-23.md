# TASK-047 P-OBS-1B bounded-attempt freshness design

## Allocation and authority

- Project / owner / base: BAI VIDEO PRODUCTION / TASK-047 / `main@09b66afc6a8899732f725313d1228dac7a3b06a9`.
- Atomic Unit: `P-OBS-1B-BOUNDED-ATTEMPT-FRESHNESS-R0-DESIGN`; DEV-4 cross-contract design. It follows the R1 terminal [gap map](p-obs-1b-native-terminal-receipt-r1-design-2026-09-23.md) and addresses **only** the R0 source/transport freshness window for one segment attempt.
- Allowed changes: this design, one bounded Task-local Evidence record, and a one-sentence `docs/ai-team/current-state.md` synchronization. No R0 schema/parser/test, TASK-046/043/003/082/098 owner contract, OBS Plugin/Controller, native runtime, private media, custody, Asset store, installer, Release or Production change.
- This design does not authorize capture START, a producer, parser implementation, native observation, receipt issuance, Asset/Dataset adoption or TASK-098 A5. Main still lacks accepted OwnerSubject/Consent, trusted-time, TASK-043 capture Job currentness and full custody/Asset bindings.

## Problem and conservative decision

R0 `CaptureSourceCurrentnessReceiptV1` is an `INITIAL` record with null predecessor. Its paired `CaptureTransportIntegrityReceiptV2` has the same segment-attempt lineage and cannot have `fresh_until` later than the source. R0 requires `created_at <= observed_at < fresh_until`; the transport cannot be created before the source observation. A single source/transport pair therefore cannot attest an attempt whose final transport/terminal observations occur after the source freshness expires. Setting a longer timestamp, treating wall time as authority, or silently relaxing the parser is not a renewal protocol.

**Decision for a bounded R1-compatible attempt:** preserve R0 wire and parser exactly. One `segment_attempt_id` is accepted for structural chaining only when all capture, stop, writer close/readback, transport receipt and terminal receipt observations can finish strictly before the earliest relevant expiry. If this cannot be guaranteed by independently bound currentness producers, refuse START. No hidden automatic new attempt, no time extension on pause and no claim of seamless long-form capture. This is a deliberately limited first scope, not a final Product duration limit. A later versioned multi-attempt/renewal design must separately own continuity and session aggregation.

## Preflight deadline and runtime state proposal

The eventual authorized producer must compute an absolute trusted monotonic deadline `D` as the earliest *verified* expiry among the source/graph selection, OwnerSubject/closed-purpose capture Consent, trusted-time binding, TASK-043 predecessor Job readback and other required capture/custody preconditions. This design does not assign these producers to TASK-047. Each UTC `fresh_until` used by the structural chain must be cross-bound by an independently verified trusted-time/currentness producer to its corresponding monotonic deadline and identity. Missing binding, disagreement, wrong domain/boot/session, stale, revoked or rollback-uncertain evidence makes `D` unavailable and START ineligible. Never derive `D` by directly comparing UTC text to a monotonic counter, or treat a structurally valid `fresh_until` as authorization.

Let `B` be a closed, verified maximum allowed time budget for stopping acceptance, draining, writer close, durable readback, transport receipt and terminal receipt issuance, and `G` a closed policy guard. All durations and deadlines use one trusted monotonic unit, are finite and overflow-checked; `requested_duration > 0`, `B >= 0`, `G > 0`. An unbound or unrepresentable value makes START ineligible. At the actual START instant `S`, revalidate every currentness/Consent/Job binding and require `S + requested_duration + B + G < D`; an earlier preflight calculation is not reusable after delay. The effective stop deadline is `min(S + requested_duration, D - B - G)`, advanced earlier on any new adverse observation. Pause time counts in the Owner-selected maximum and never extends `D`. Do not silently shorten that maximum: the UI may explain the safe bound and ask for a shorter Human choice, but must not start a different duration without it. No per-packet filesystem or cryptographic work enters the OBS callback.

At the effective stop deadline, or earlier on source/OBS/process drift, Consent revocation, Job/head change, time-domain uncertainty, device loss or transport failure, the future controller must stop accepting new frames and enter a distinct stop/recovery state. Exceeding `B` is a failure, never a deadline extension. Writer close/readback of a partial raw object may still be recorded for recovery, but that is not complete capture, TASK-082 custody, TASK-003 Asset or Dataset admission. If finalization or receipt issuance cannot be proven before `D`, no fresh terminal-chain claim is emitted; the attempt remains `UNKNOWN`/quarantined for exact recovery. A lost reply or restart cannot mint a second terminal or silently continue the same attempt.

## Structural time contract for the bounded subset

The R1 terminal ABI design may use the following **bounded-subset** ordering only after its own exact field matrix is frozen:

```text
source.created_at <= source.observed_at <= capture_started_at
capture_started_at <= capture_finished_at <= transport.created_at
transport.created_at <= transport.observed_at <= terminal.created_at
terminal.created_at <= terminal.observed_at < terminal.fresh_until
terminal.fresh_until <= transport.fresh_until <= source.fresh_until
```

Equality at an expiry is invalid. These UTC comparisons are structural and **separate** from the trusted monotonic `D` check; both must pass, and disagreement fails closed. Neither proves that any timestamp, Consent, source graph, HMAC, Job/head or terminal writer actually came from a trusted current producer. The distinct receipt digests and R0 `_LINEAGE_FIELDS` remain required. A normal stop near expiry that misses the final deadline is `UNKNOWN`, not a successful terminal. The future R1 design must still settle writer-versus-capture completeness, raw readback, pause and acoustic matrices independently; this document does not freeze its schema.

## Long-session boundary and test vectors

- A fresh attempt after an earlier attempt is conclusively closed must have a new `segment_attempt_id`, independent source/transport pair, fresh currentness/Consent/Job preflight and a separate terminal/recovery outcome. After an `UNKNOWN` result, exact durable reconciliation is required before any replacement attempt; no lost reply may be bypassed. R0 `INITIAL` cannot be used as a pretend renewal inside the same attempt. This design does **not** aggregate attempts into one continuous recording session or let one attempt's expiry/custody authorize another.
- A later uninterrupted/rolling long-capture capability needs its own versioned checkpoint/renewal ABI and TASK-046 session/segment, TASK-043 Job/head, TASK-082 custody and TASK-003 Asset composition review. Until then, a requested attempt longer than the verified safe window is refused rather than truncated silently.
- Structural test layer (future R1 parser): bounded receipt timestamps with strict inequalities; equality at each source/transport/terminal UTC expiry; wrong predecessor, stale lineage and terminal after source expiry. R0 parser remains unchanged and cannot evaluate current time, revocation, `D/B/G`, producer authenticity or durable state.
- Producer/state test layer (separate future authorized unit): inject a verified monotonic deadline/clock, UTC-to-monotonic binding and durable attempt journal. Cover START after delayed preflight, `S + duration + B + G < D` versus equality, stop at `min(S + duration, D - B - G)`, pause consuming duration, expiry/revocation at START/during pause/after stop before final receipt, `B` overrun, rollback/boot substitution, disagreement with UTC receipt fields, lost reply before and after durable terminal publication, restart/same-attempt replay, and new attempt after `UNKNOWN`. A closed/read-back partial raw object is recovery-only. These producer/state cases are **NOT_EXECUTED / NOT_CONFIRMED**; this design grants no implementation authority. Tests must never promote `STRUCTURAL_VALID_ONLY` into authenticated admission.

## Acceptance and next action

This unit is complete only as a reviewed **bounded-attempt design decision**. It resolves the R1 gap map's long-capture contradiction for short, explicitly bounded attempts without changing R0. It does **not** solve seamless long recording, grant implementation/native authority or unblock TASK-098 A5. Before any runtime/code unit, independently freeze `B/G` policy ownership, trusted monotonic deadline producer, stop/recovery behavior and R1 terminal matrices, then perform fresh DEV-4 review. No assumed default TTL, recording duration or time-skew value is introduced here.
