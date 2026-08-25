# TASK-029 R9C — Local Knowledge Pack Signing Ceremony Design / Critic / Judge

Date: 2026-08-26
Governance: DEV-4 PRIVACY, LEARNING AND RELEASE INTEGRITY
Unit: R9C exact local signing and immediate R9A verification

## Goal

R9C closes the in-process gap between R9B encrypted Owner signing-key custody and R9A detached-signature verification. It revalidates exact R8 compile inputs before key access, requires explicit Human confirmation bound to the exact custody receipt and signature request, signs only the R8 sha256-prefixed ASCII message, and immediately verifies that signature through R9A.

## Contract

- R8 current-source recompilation and request equality run before custody access.
- The trusted signer policy must be ACTIVE, match the request policy hash, and contain the custodied key ID.
- The caller-supplied custody receipt must equal a fresh decrypt-and-verify read from the R9B store.
- Human confirmation binds ceremony ID, exact custody receipt SHA and exact signature request SHA.
- R9B reloads custody while holding its exclusive lock immediately before signing.
- The private seed is never returned; public key and detached signature exist only inside the call and are immediately consumed by R9A.
- The returned ceremony receipt and R9A receipt contain hashes only.

## Replay and persistence boundary

R9C has no ceremony journal and therefore does not claim durable one-shot replay prevention. Repeated execution for the same exact request is deterministic but still requires the exact Human-confirmation object. The public receipt fixes `persistent_replay_prevention_present=false`.

A later Pack-write Unit must add durable idempotency/replay state before it can persist a signature or Knowledge Pack. R9C does not return detached signature bytes and cannot write or promote a Pack.

## Failure modes

| Failure | Required result |
|---|---|
| stale/tampered R8 request | reject before custody decrypt |
| revoked or mismatched signer policy | reject before custody decrypt |
| caller custody receipt differs from current store | reject |
| signer key ID not admitted by request/policy | reject |
| Human confirmation differs from custody/request | reject before signing |
| custody changes between read and signing | reject under exclusive lock |
| generated signature fails R9A verification | reject; no receipt |
| receipt unknown field or authority drift | reject |

## Authority boundary

R9C source authorizes only an explicitly confirmed local in-memory signing ceremony. This implementation and its tests use synthetic keys only. No real Owner key is created, imported, decrypted or used during development verification.

R9C does not authorize signature export, Pack write/promotion, automatic promotion, runtime Profile apply, rollback, Release, Deploy, Production, Resolve/Timeline, Provider/Cloud or external effects.

## Critic

- High: the initial draft described local signing as one-shot without a durable journal. Resolved by removing that claim and exposing `persistent_replay_prevention_present=false`.
- High: a stale request could cause key access. Resolved by exact R8 revalidation before any custody read.
- High: a key could sign for a revoked or unrelated policy. Resolved by active policy/hash/key-ID admission before signing and by immediate R9A verification.
- Medium: signature or key bodies could escape through results. Resolved by returning only body-free hash receipts.
- Medium: custody could drift between policy checks and signing. Resolved by a second custody load under the R9B exclusive lock and exact receipt equality.

Residual Critical/High/Medium/Low: 0/0/0/0.

## Tester evidence

- R9C focused synthetic tests: 7 PASS
- Schema mirror and strict Draft 2020-12 validation: PASS
- request tamper and revoked-policy rejection before custody decrypt: PASS
- wrong custody, confirmation, completion time and receipt tamper negatives: PASS
- Python compile: PASS
- R8/R9A/R9B/R9C direct regression: 33 PASS
- TASK-029 regression: 101 PASS
- full Product regression: 3906 PASS / 6 SKIP / 0 FAIL
- hosted independent review: pending

## Judge

Decision: GO for bounded local implementation and regression. Hosted integration requires the normal exact CHANGELOG lock transaction. This decision does not authorize real Owner signing or a real-key native ceremony.