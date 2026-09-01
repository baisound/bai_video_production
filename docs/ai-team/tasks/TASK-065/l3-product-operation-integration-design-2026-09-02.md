# L3 Product-operation / TASK-065 integrated consumer design

State: `TASK_LOCAL_DESIGN_ONLY / RECEIPTS.N.C. / EXE_START0 / EFFECT0`

This packet joins the TASK-036 packaged Product-operation design with
TASK-065 PL-A/B/C/D consumption. It is a design-only companion to
`l3-one-way-receipt-crosswalk-2026-09-02.md`; Draft PR #467 is the sole
carrier and never merge authority. It authorizes no Canonical SKILL/BVP source
change, installed-config mutation, executable build/install, real E2E, or
Production Activation.

## Exact one-way producer / consumer join

```text
TASK-069 U1a-c + TASK-060 + TASK-063 + D2S interface readback
  -> TASK-061-A (enabled:false) -> TASK-067
  -> TASK-036 private Product operation
     stage exact1 -> import_path exact1 -> pinned BVP receipt/correlation/Profile
  -> D2S_001_OPERATION_TERMINAL_HANDOFF_V1
  -> TASK-061-B (enabled:false) -> TASK-065 PL-A/B/C/D read/join
```

TASK-069 U1a-c has no delivered canonical allocation, schema, or receipt
identifier, so it remains `TASK069_U1A_C.N.C. / EFFECT0`; no proposed field,
fixture or status can replace it. TASK-060 and TASK-063 likewise contribute
only their future owner-issued durable receipts. Canonical SKILL main/tree
identity is audit-only; TASK-061-A requires the separately pinned
`D2S_001_INTERFACE_COMPLETION_READBACK_V1` binding installed bytes plus
H1/H2/v2 completion.

## Packaged Product-operation ABI

The future private TASK-036 EXE route receives only an opaque operation-plan
identity and an opaque record identity resolved by the trusted Product
resolver. It must resolve all selected installation, descriptor/owner,
immutable config, adapter, bridge and Profile coordinates internally from the
same one-use operation snapshot.

| Ineligible EXE/consumer input | Required result |
| --- | --- |
| raw path, root, revision, store, mode, output path, config body, learning body, receipt body, Profile body, ticket, timestamp or clock | `PRODUCT_OPERATION_INPUT_INVALID / EFFECT0` |
| caller-selected instance/build, `--config`, `--learning`, `--output`, discovery refresh, inbox scan or `import_once` | `PRODUCT_OPERATION_INPUT_INVALID / EFFECT0` |
| copied/deserialized plan or record, public type/hash/seal, stale/cross-instance digest | `OPERATION_CURRENTNESS.N.C. / EFFECT0` |

`TASK036_D2S_EXECUTION_HANDOFF_V1` is private dispatch authority and is not a
TASK-061-B or TASK-065 ABI field. It atomically burns its one-use capability
before the stage; direct CLI/copy/replay/cross-command entry is closed. The
consumer-visible successor is body-free
`D2S_001_OPERATION_TERMINAL_HANDOFF_V1` with opaque identities/digests only
and `authority_created:false`.

## Terminal receipt binding / consumer acceptance

The D2S terminal handoff must bind one exact operation, selected instance and
immutable v2 snapshot to all of the following pinned readbacks:

| Binding group | Required evidence | Reject / local result |
| --- | --- | --- |
| product plan | opaque plan and record identities; future TASK-069 U1a-c canonical allocation/schema/receipt identity/digest (all N.C. until owner issuance); TASK-060 strict source/promotion receipt identity/digest; TASK-063 selected instance/descriptor/owner receipt identity/digest; `TASK061_PREACTIVATION_PREPARE_V1`, `TASK067_GENERIC_FACADE_COMPLETION_V1`, and `D2S_001_INTERFACE_COMPLETION_READBACK_V1` issuer/message-version/receipt digests | any absent/mixed N.C., issuer/version/digest, canonical allocation/schema identity, or caller reconstruction -> `PREACTIVATION_CHAIN.N.C. / EFFECT0` |
| exact-one transport | stage count=`1`, TASK-036 `import_path` count=`1`, expected command/result digests and zero retry/scan counters | count not one, second publish/import, replay or crash retry -> `EXACT_ONE_VIOLATION / FAILED_CLOSED / EFFECT0` |
| BVP terminal state | strict public receipt digest, hidden correlation digest, canonical Generic/Project readback digest and advisory Profile readback digest | receipt-only, `canonical_store_written`, status-only, missing/wrong Profile or correlation -> `TERMINAL_HANDOFF.N.C. / EFFECT0` |
| security/currentness | strict canonical bytes/raw bytes/physical identity, trusted clock/expiry, selected user/session/build/native backend | path swap, stale/cross-instance/clock/config drift or unknown physical identity -> `OPERATION_CURRENTNESS.N.C. / EFFECT0` |
| public projection | opaque IDs/digests, typed outcome, `authority_created:false`, no raw private value | path/body/token/SID/account/OS detail leak -> `PUBLIC_PROJECTION_REJECTED / EFFECT0` |
| downstream final closure | `TASK061_FINAL_CA_C_COMPLETION_V1` issuer/message-version/receipt digest; `enabled:false`; same `D2S_001_OPERATION_TERMINAL_HANDOFF_V1` operation/instance/config/build digest | public/copy/rehash projection, wrong/stale/cross-operation binding, or `enabled:true` -> `PREACTIVATION_CHAIN.N.C. / EFFECT0` |

TASK-061-B may freshly consume only the terminal handoff through the downstream
final-closure binding above and must retain `enabled:false`. TASK-065 PL-A/B/C/D
only pinned-read and validate the terminal handoff plus this exact TASK-061-B
issuer/message-version/receipt-digest and same-operation join; it invokes
adapter/TASK-036 zero times and has local
Project/Bridge/Profile/config/history/Activation delta zero. No public receipt,
hash, fixture, UI state or `canonical_store_written` creates consumer
authority. Its body-free consumer result is
`TASK065_M1_IMPORT_CONSUMER_VALIDATION_V1` with opaque receipt digests only and
`authority_created:false`.

## Preactivation and post-activation separation

| Phase | Entry condition | Permitted behavior | Forbidden substitution |
| --- | --- | --- | --- |
| preactivation | all upstream durable receipts current; TASK-061-B remains `enabled:false` | terminal read/join only; historical stage/import counts may be observed | use as connector enable, second publish/import, retry ticket or post-activation authority |
| post-activation | a distinct current Production Activation Human receipt, a new operation ID and a new one-shot ticket | separately authorized exact 0/1 operation and new readback | reuse a preactivation plan, delivery, handoff, receipt, ticket, config or operation ID |

The current Authority includes neither condition, so both real-effect paths are
`START0 / GATE_REQUIRED / EFFECT0`.

## Crash, restart, privacy and replay matrix

| Seam | Required closed behavior | UI / next action |
| --- | --- | --- |
| before ticket redemption | no stage/import; capability unavailable | `NOT_CONFIRMED`; wait for current upstream receipt |
| after redemption or stage, before import result | same operation is `FAILED_CLOSED`; effect certainty remains producer-owned 0/1 and second dispatch is zero | `FAILED_CLOSED`; fresh producer resolver only, no TASK-065 retry |
| after import, before terminal handoff | preserve producer evidence; no second publish/import or receipt probe | `NOT_CONFIRMED`; wait for pinned terminal handoff |
| terminal handoff/readback mismatch or restart | preserve state; no repair/delete/overwrite or capability reuse | `PREACTIVATION_CHAIN.N.C.`; request a new owner-issued resolver result |
| privacy/strict-JSON/currentness failure | body-free rejection; raw sensitive data absent from UI/log/receipt/temp | `NOT_CONFIRMED`; correct upstream producer only |
| complete preactivation validation | no local effect and no activation implication | `PREACTIVATION_CHAIN_VALIDATED`; next action is separate Human Activation Gate |
| post-activation request without Human receipt | no adapter/TASK-036 call and no config/history change | `GATE_REQUIRED`; request the separate Human Gate, not an ACK/retry |

No screen state may display `READY`, `PASS`, an absolute path, raw receipt,
correlation, Profile, account/SID, secret, or private learning content. The
only public next-action values are body-free `NOT_CONFIRMED`,
`PREACTIVATION_CHAIN.N.C.`, `FAILED_CLOSED`,
`PREACTIVATION_CHAIN_VALIDATED`, and `GATE_REQUIRED`.

## Completion boundary

This integrated design is complete when its task-local static contract remains
green. Runtime completion remains N.C. until every owner-issued receipt above
is independently current and the separate Human Activation Gate is satisfied.
