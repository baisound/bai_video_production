# M1 import-consumer / TASK-067 / TASK-065 integration design

State: `TASK_LOCAL_DESIGN_ONLY / CANONICAL_ALLOCATION.N.C. / EFFECT0`

This packet closes only the consumer-side contract. It does not allocate
TASK-067, create a Generic facade, issue a ticket, import a record, mutate a
Project or Bridge, synchronize an installed SKILL, or authorize Activation.

## M1 role and issuance boundary

M1 is a **read-only import consumer**, never an authority issuer. It can
request a pinned validation join only after the canonical TASK-067 owner has
issued a durable `TASK067_GENERIC_FACADE_COMPLETION_V1` record. It cannot mint,
copy, deserialize, rehash or select that record; a public Generic object,
fixture, status, plan or TASK-061-A receipt is not an M1 validation input.

Absent or inconsistent input returns `M1_IMPORT_CONSUMER.N.C. / EFFECT0`.
M1 does not retry TASK-067, adapter staging or TASK-036 import and cannot turn
an `N.C.` result into a ticket or a later lifecycle authority.

## Requested TASK-067 canonical allocation

Until a canonical owner publishes this allocation, every row is a requested
boundary, not authorization to edit source.

| Item | Required canonical allocation |
| --- | --- |
| Task identity | `TASK-067 Generic Review Operation Facade`, owner and versioned completion issuer |
| Allowed source | `montage_learning_generic_operation.py` and its focused test; no activation, installation, TASK-036, SKILL, exact-lane, public config/hash/seal authority minting |
| Limited amendment | only the private Generic factory, `admit_generic_observation`, `recover_generic_observation`, `get_verified_generic_observation`, and directly necessary Generic manifest/journal snapshot helper in the TASK-058 canonical-admission boundary |
| Required effects | explicitly declared FRESH / PRECOMMIT_RESUME / JOURNAL_RECOVERY generations; read-only VERIFIED_READBACK; all effects unavailable until the canonical owner closes the write protocol |
| Completion receipt | body-free `TASK067_GENERIC_FACADE_COMPLETION_V1`, durable pinned snapshot, no private capability serialization |

The canonical receipt must bind its canonical task main identity, closed facade
ABI digest, same-snapshot Generic manifest and terminal-journal digests, exact
TASK-061-A prepare receipt digest, operation/instance/config/build coordinate,
typed terminal result and `authority_created:false`. It must reject a caller
mode, cross-operation receipt, mixed physical identity, public factory, copied
mapping, absent journal, stale terminal, or exception/replay claim.

## TASK-065 PL-A versioned consumer ABI

M1/PL-A reads the producer records in this order; no local effect is allowed:

```text
pinned D2S_001_INTERFACE_COMPLETION_READBACK_V1
  -> TASK-061-A prepare (enabled:false)
  -> TASK-067 canonical completion
  -> TASK-036 exact-one operation handoff
  -> TASK-061-B final completion (enabled:false)
  -> TASK-065 pinned PL-A consumer join
```

The canonical SKILL main/tree identity is an audit-only side observation. It
has no dependency edge and cannot substitute for the separately pinned D2S
completion readback, which must bind the installed bytes and H1/H2/v2 snapshot
completion before TASK-061-A may proceed.

TASK-069 is currently absent from canonical allocation, so its proposed
terminal-readback shape is explicitly `N.C.` and cannot be inserted as a
substitute. The future M1 consumer validation result is body-free
`TASK065_M1_IMPORT_CONSUMER_VALIDATION_V1`; it contains only opaque producer
receipt digests, a typed `NOT_CONFIRMED`/`VALIDATED` state and
`authority_created:false`. It contains no raw path, ticket, record body,
config, owner scope, secret, correlation body or capability.

## Negative acceptance matrix

| Fault | Result | Local delta |
| --- | --- | ---: |
| TASK-067 absent / no canonical owner / no durable receipt | `TASK067_CANONICAL_ALLOCATION.N.C.` | 0 |
| M1 direct import, direct factory, public/copy/rehash receipt | `M1_IMPORT_CONSUMER.N.C.` | 0 |
| TASK-061-A/B or TASK-036 version/issuer/digest mismatch | `UPSTREAM_RECEIPT_MISMATCH` | 0 |
| stage/import count not exactly one, second publish/import, receipt-only or `canonical_store_written` | `PREACTIVATION_CHAIN.N.C.` | 0 |
| TASK-069 proposal/fixture/status used as a receipt | `TERMINAL_READBACK.N.C.` | 0 |
| installed sync, real E2E, connector enable or Activation requested | `GATE_REQUIRED / EFFECT0` | 0 |

## Design completion boundary

This packet is complete when its task-local fixture and focused test maintain
the listed `null` / false placeholders and body-free effect-zero outcomes. It
does **not** make TASK-067 canonical, issue any producer receipt, satisfy
TASK-036, or authorize a design PR. A design PR remains prohibited until the
owner confirms the full task-local packet is the intended sole design change.
