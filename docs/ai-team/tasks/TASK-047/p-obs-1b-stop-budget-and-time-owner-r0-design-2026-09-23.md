# TASK-047 P-OBS-1B stop budget and trusted-time owner boundary

## Allocation, authority and scope

- Project / Task / base: BAI VIDEO PRODUCTION / TASK-047 / `main@7ce971256525bdf9bed8200ef006e67ee2bf4c94`.
- Atomic Unit: `P-OBS-1B-STOP-BUDGET-AND-TIME-OWNER-R0-DESIGN`; DEV-4 because stop completion, time/currentness and private capture recovery cross Product responsibility boundaries.
- Owner's TASK-047 receipt ABI/parser continuation plus the merged [bounded-attempt freshness design](p-obs-1b-bounded-attempt-freshness-r0-design-2026-09-23.md) authorize this design investigation, not native Controller mutation or recording. Allowed Files: this design, bounded Task-local Evidence and one current-state synchronization. No source/test/schema, other Task owner contract, OBS/native runtime, private media, custody, Asset, installer, Release or Production mutation in this unit.
- Decision status: **boundary proposal and exact-source gap audit**, not numeric budget acceptance, trusted-time owner assignment, R1 ABI freeze, producer readiness or capture START.

## Current implementation reality

The existing Technical Preview Controller is not the bounded-attempt producer:

1. `BaiVoiceCaptureController.cs` sets `maximumMinutes` to 1–120 (default 90), but `GetActiveElapsed()` subtracts pause time and uses `DateTime.UtcNow`. The merged bounded-attempt design instead counts pause against the Owner-selected maximum and requires trusted monotonic timing. The old UI limit cannot be reused as proof of that design.
2. `BeginStop()` requests stop and calls `BeginSettlementAsync(2000 ms)`. If settlement exceeds that period, `SettleAndFinalizeAsync()` calls `AwaitSettlementWithoutDeadlineAsync()`. The latter waits until receiver, teardown and in-flight leases settle with no deadline. Thus 2000 ms is not a finite stop/finalization budget `B`.
3. After settlement, `FinalizeSettledOperation()` finalizes a float WAVE prefix, may `File.Move` a partial file and writes a legacy receipt. This is not a bounded durable raw readback, TASK-082 encrypted custody, TASK-003 Asset adoption or canonical PCM24 terminal chain. It has no accepted receipt-issuance deadline.
4. TASK-082 Windows custody takes an injected `trusted_time_provider` returning a validated UTC string; it does not establish the TASK-047 boot/session-bound monotonic `TrustedCaptureTimeBindingV1` producer. TASK-043 owns Job/head currentness, not implicitly a clock. No current BVP owner is bound for that capture-time producer.

## Proposed TASK-047 stop-budget contract

TASK-047 may own the capture stop/finalization policy for its own future producer, but it must consume—not mint—the verified time/currentness binding. The policy version must bind the exact Controller/worker build, source format path, selected output role, stage budgets, guard derivation, evidence revision and failure transition. A configuration value or self-reported receipt is not native timing proof or implementation authority.

Let `B` be checked sum of closed, finite, nonnegative per-stage *maximum allowed execution budgets* in one trusted monotonic unit:

1. `b_stop`: linearize stop and reject all new packet leases;
2. `b_settle`: cancel/close the owned receiver, teardown and wait for all in-flight leases to settle;
3. `b_writer`: close/flush the operation-owned raw writer without publishing an Asset;
4. `b_readback`: durable same-object readback, byte-count/hash/physical-identity check and quarantine on ambiguity;
5. `b_receipts`: issue/persist the exact body-free transport/terminal records and read them back.

`G > 0` is a separately versioned guard for verified UTC↔monotonic mapping uncertainty, timer scheduling/observation lag and policy margin. No numeric `B`, component or `G` is accepted from the existing 2-second settlement call, a unit test, wall-clock `DateTime.UtcNow`, or an unobserved Windows scheduling assumption. Numeric values require a bounded native fault/latency study under an independently authorized gate. Unknown value, overflow, missing build binding or nonpositive `G` makes START ineligible.

The accepted bounded-attempt inequality uses the actual START instant `S`: `S + requested_duration + B + G < D`, where `D` is the earliest independently verified currentness expiry in the same monotonic domain. The stop threshold is `min(S + requested_duration, D - B - G)`; pause consumes the requested duration. At each stage, a timeout stops *authority to claim completion*; it does not pretend that an uncooperative receiver/OS operation physically completed. Preserve ownership and the exact partial/recovery state; mark `UNKNOWN`/quarantined, block new attempt and reconcile from durable evidence. Never finalize/move a file while packet leases remain in flight, delete the partial object to make the timeout appear clean, extend `D`, or silently fall back to unlimited waiting while reporting success. Emergency stop remains usable even when ordinary START is ineligible.

**High implementation prerequisite, not resolved by this design:** a synchronous lock acquisition or writer flush can block the same control flow that would observe its own timeout. A future code unit must provide independent deadline observation/supervision, a durable attempt journal and restart readback so `UNKNOWN` and reuse prohibition survive a stuck operation or process crash. A pure reducer test cannot prove physical stop, quarantine or that a blocked OS call was released. No future runtime START claim is valid until this mechanism and its failure modes are independently reviewed and proven on the exact target.

Successful structural terminal issuance additionally requires both the trusted monotonic deadline check and the R0/R1 UTC ordering check; a signed-looking digest or matching `fresh_until` cannot substitute for either. Revocation, source/OBS/process drift, boot/domain mismatch, clock rollback, Job/head change or missed stage deadline stops acceptance early and forbids admission. Writer close/readback of partial bytes may remain recovery evidence only.

## Responsibility and gates

| Responsibility | Proposed/canonical owner | Boundary |
|---|---|---|
| Stop/settlement/writer stage orchestration and `B/G` policy | TASK-047 capture producer, after separate implementation allocation | Does not own trusted time, Consent, Job CAS, custody, Asset or Dataset. |
| `TrustedCaptureTimeBindingV1` boot/session/monotonic-to-UTC producer | **UNALLOCATED** | Requires explicit canonical owner/Task allocation. TASK-043 Job currentness and TASK-082 UTC provider are consumers/adjacent capabilities, not proof of this owner. |
| Durable capture Job/head and terminal CAS readback | TASK-043 | TASK-047 cannot select or self-attest the current terminal. |
| Private raw/canonical media custody | TASK-082 | A writer/readback receipt is not a custody lease or receipt. |
| Capture Asset registration/readback | TASK-003 | No path/hash-only Asset promotion. |
| Voice recording/Dataset truth; OwnerSubject and closed-purpose capture Consent | TASK-046 for voice/Dataset responsibility; exact subject/Consent producers **UNALLOCATED** | Capture Consent does not grant Dataset adoption/training, and TASK-047 cannot mint either binding. |

The time-producer ownership gap is a **shared implementation START blocker**; this design does not allocate it to TASK-047, TASK-043 or TASK-082 by inference. A future owner decision must specify the versioned binding ABI, restart/boot-domain semantics, rollback detection, issuer authenticity and how each UTC `fresh_until` is cross-bound to an independently verified monotonic deadline. No Owner choice is needed merely to keep this design/intake lane moving.

## Verification plan and next action

- Pure future state tests: checked budget sum/overflow; positive finite durations; actual-START revalidation; selected maximum including pause; strict equality at each stage and aggregate `B`; timeout before stop linearizes, after writer close but before durable receipt publication, and while receiver remains active; lost reply before/after durable terminal; restart and UNKNOWN reconciliation. These prove only state decisions, not physical stop. The existing `test_task047_readiness_monitor_source_contract.py` explicitly pins the legacy 2-second/unbounded-fallback source and must be deliberately migrated in a later authorized implementation rather than cited as budget proof.
- Future native/fault Evidence: exact supported build, owner-marked output root, independent deadline observer and durable attempt journal/readback under load; inject stuck lock, delayed/cancel-resistant receiver, flush/readback stall, process crash, restart with pending cleanup and refusal of same-attempt reuse. No final `File.Move` or legacy success projection may follow an unresolved timeout. Native execution is **NOT_EXECUTED / NOT_CONFIRMED** in this design unit and needs its own bounded Human Gate.
- Next bounded work: obtain a canonical trusted-time owner allocation and exact producer contract; separately design/implement TASK-047's finite stop state machine and budget policy after source review, then independently verify R1 terminal matrices. Until then `B/G=UNBOUND`, `D=NOT_BOUND`, R1 ABI remains unallocated and TASK-098 A5 remains blocked.
