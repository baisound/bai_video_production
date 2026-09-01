# L3 one-way receipt / consumer crosswalk

State: `TASK_LOCAL_DESIGN_ONLY / ALL_UPSTREAM_RECEIPTS.N.C. / EFFECT0`

This is the sole consumer-side crosswalk for TASK-065 Draft PR #467. It does
not allocate any upstream Task, mint a receipt, authorize a source change, or
make a real-installed, installed-sync, connector-enable, or Production
Activation effect. No additional design PR may be created: the existing Draft
PR #467 is the only carrier, and it is not merge authority.

## Authoritative direction

```text
TASK-068 -> {TASK-069 U1a-c, TASK-063} -> TASK-060
{TASK-069 U1a-c, TASK-060, TASK-063, D2S interface readback}
  -> TASK-061-A prepare (enabled:false) -> TASK-067
{TASK-061-A, TASK-063, D2S interface readback, TASK-067}
  -> TASK-036 private exact-one operation
  -> D2S operation terminal handoff -> TASK-061-B final CA-C (enabled:false)
  -> TASK-065 PL-A validation reader
```

The future TASK-069 terminal reader may observe a completed TASK-036 operation
without adding a reverse implementation dependency. The private
`TASK036_D2S_EXECUTION_HANDOFF_V1` never crosses into TASK-061-B or TASK-065;
the latter two may read only the future body-free
`D2S_001_OPERATION_TERMINAL_HANDOFF_V1` after independently pinned producer
readback.

## Receipt and consumer ABI crosswalk

| Producer / state | Canonical output required before its consumer may proceed | Consumer rule | Current result |
| --- | --- | --- | --- |
| TASK-069 U1a-c | Canonical allocation, versioned schema and durable receipt identifiers for U1a/U1b/U1c are all required. The receipt must cover FB-R/C/P/X/PR, PRIV, HEAD and executed READY/TASK058 baseline readback. | No caller status, fixture, hash, code-presence, `safe_export`, or proposed U1 field is a substitute. | `TASK069_U1A_C.N.C. / EFFECT0` |
| TASK-060 | Product-owned strict DPAPI source/promotion completion bound to selected instance/current user, Human transaction and same snapshot. | TASK-061-A consumes only its durable current completion, never a public source object or caller cipher/coordinate. | `TASK060_SOURCE.N.C. / EFFECT0` |
| D2S | Pinned `D2S_001_INTERFACE_COMPLETION_READBACK_V1`: installed bytes plus H1/H2/v2 strict snapshot completion. Canonical main/tree identity is audit-only. | TASK-061-A requires this separate pinned receipt; source identity alone has no graph edge. | `D2S_INTERFACE.N.C. / EFFECT0` |
| TASK-061-A | `TASK061_PREACTIVATION_PREPARE_V1`, exact CA-A/B correction and sealed CA-C plan/config/challenge, `enabled:false`. | TASK-067 receives this prepare receipt only; no activation authority crosses. | `TASK061A.N.C. / EFFECT0` |
| TASK-067 | `TASK067_GENERIC_FACADE_COMPLETION_V1`, issued by a canonical owner after the allocated Allowed Files and closed Generic facade ABI complete. | TASK-036 consumes the durable completion only. Public factory/type/hash, preserved diff and fixture remain ineligible. | `TASK067_CANONICAL_ALLOCATION.N.C. / EFFECT0` |
| TASK-036 | Private `TASK036_D2S_EXECUTION_HANDOFF_V1` redeems one internal dispatch only. Its independently pinned producer state must later support a body-free `D2S_001_OPERATION_TERMINAL_HANDOFF_V1`. | TASK-061-B/TASK-065 do not read, compare, copy or deserialize the private dispatch handoff. | `TASK036_HANDOFF.N.C. / EFFECT0` |
| TASK-061-B | `TASK061_FINAL_CA_C_COMPLETION_V1`, freshly composed from the exact D2S terminal handoff, retaining `enabled:false`. | TASK-065 validates receipt identity/currentness only; Production Activation needs a separate Human Gate. | `TASK061B.N.C. / EFFECT0` |
| TASK-065 PL-A/M1 | Body-free `TASK065_M1_IMPORT_CONSUMER_VALIDATION_V1` containing only opaque receipt digests and `authority_created:false`. | Read/join only: adapter, TASK-036, install, config, Profile, history and Activation deltas are all zero. | `PREACTIVATION_CHAIN.N.C. / EFFECT0` |

## TASK-067 canonical identity / Allowed Files gate

Before source start, a canonical owner must allocate `TASK-067 Generic Review
Operation Facade` with only `montage_learning_generic_operation.py`, its
focused test and TASK-067-local docs. A bounded TASK-058 amendment may contain
only a private Generic factory, `admit_generic_observation`,
`recover_generic_observation`, `get_verified_generic_observation`, and direct
Generic manifest/journal snapshot helpers in exactly
`src/ai_video_production/montage_learning_canonical_admission_transaction.py`;
no other TASK-058 path is allowed. Exact lane, public receipt, Profile,
Timeline, activation, installation, TASK-036, SKILL, and public
config/hash/seal authority minting remain outside that allocation.

## Consumer-negative closure

| Fault | Required result | TASK-065 local delta |
| --- | --- | ---: |
| Any U1a-c field/receipt is absent, public, stale or caller-derived | `TASK069_U1A_C.N.C. / EFFECT0` | 0 |
| D2S main/tree identity replaces interface readback | `D2S_INTERFACE.N.C. / EFFECT0` | 0 |
| TASK-067 candidate/preserved diff/public object replaces canonical completion | `TASK067_CANONICAL_ALLOCATION.N.C. / EFFECT0` | 0 |
| Private TASK-036 dispatch handoff is offered to TASK-061-B/TASK-065 | `TERMINAL_HANDOFF.N.C. / EFFECT0` | 0 |
| Terminal handoff or TASK-061-B is missing, mixed, stale or cross-instance | `PREACTIVATION_CHAIN.N.C. / EFFECT0` | 0 |
| Any request to stage, import, enable, install, sync, activate or retry | `GATE_REQUIRED / EFFECT0` | 0 |

The crosswalk is closed as design only. It remains a consumer checkpoint until
each named canonical receipt is independently issued and pinned-read.
