# TASK-029 R10C Signature Artifact Custody Candidate — Design / Critic / Judge

Date: 2026-08-27

Status: IMPLEMENTATION_REVIEW_PENDING

DEV profile: DEV-4 FOUNDATION CRITICAL

## Atomic Unit

R10C consumes the machine-readable R10B next state
`READY_FOR_INITIAL_SIGNATURE_ARTIFACT_CUSTODY`. It creates one body-free,
in-memory candidate for a later Owner-local signature-artifact custody
transaction. It does not write public-key or signature bytes and does not
claim that custody exists.

Allowed paths are this design, the TASK-029 task record, one new public schema
and package mirror, one new Product module and one focused test module.
CHANGELOG.md, ACTIVE-WORK-LOCKS.json, stores, installers, UI, Resolve, Timeline,
runtime Profile application, release and production paths are outside this Unit.

## Inputs and algorithm

1. Accept body-free R9B key-custody, R9C signing-ceremony and R10B trusted
   signature admission payloads.
2. Snapshot each public JSON payload exactly once into bounded built-in
   `dict`/`list`/scalar values. Custom Mapping hooks, derived scalar classes,
   non-JSON values, excessive depth and excessive node counts fail closed.
3. Reconstruct the exact typed R9B, R9C and R10B receipts and verify each
   canonical self-hash and fixed authority boundary.
4. Require R9C to bind the exact R9B custody receipt. Require R9C ceremony,
   signature request, signer key, detached-signature digest and verification
   receipt coordinates to equal R10B exactly.
5. Carry the Owner scope only from the R9B encrypted signing-key custody
   receipt. Require that custodied signer to equal the R10B signer.
6. Require candidate creation time to be at or after R9B custody, R9C
   completion and R10B verification.
7. Return an immutable candidate containing hashes and stable identifiers only.

## Output and authority boundary

The candidate records that a later write must:

- direct-recompile R10B with transient public-key and detached-signature bytes;
- repeat cryptographic verification at the write boundary;
- require explicit Human custody confirmation;
- use an Owner-local encrypted, one-shot artifact store.

The candidate is publicly constructible and non-authoritative. It includes no
artifact body, public/private key material, host path or credential. Artifact
The R9B/R9C/R10B receipts are self-validated, but source-graph currentness and
Owner-scope origin authentication remain false until the later write boundary
directly recompiles R10B and consults a canonical Owner trust source.
custody write, custody confirmation, canonical receipt, canonical trust root,
Owner signer binding, Knowledge Pack write/promotion, automatic promotion,
runtime apply, rollback, Release and external effects are fixed false.
Project and reviewer coordinates are not yet present.

## Failure model

| Threat | Required result |
|---|---|
| custom/stateful Mapping | reject before hook read |
| derived `str`/`int` security scalar | reject |
| R9B receipt drift | reject |
| R9C custody/request/signer/signature/verification drift | reject |
| R10B state or self-hash drift | reject |
| Owner signer mismatch | reject |
| candidate time before any exact source | reject |
| output authority flag or hash tamper | reject |
| unknown output field | reject |
| raw artifact/key/path/credential persistence | impossible from public output |

## Verification plan

- valid R9B/R9C/R10B projection and strict schema validation;
- byte-identical package schema mirror;
- body/secret absence and fixed authority flags;
- custody, ceremony and admission cross-binding negatives;
- source causality negatives;
- custom Mapping zero-hook and scalar-subclass negatives;
- output flag/hash/unknown-field negatives;
- immutable dataclass and AST no-I/O capability audit;
- focused R10C, direct R9B-R10C/TASK-029 and full Product regression;
- exact-path/diff review and independent DEV-4 Critic/Tester/Judge.

## Builder Critic

Initial findings C/H/M/L: `0/2/2/0`.

Resolved High findings:

1. R10B alone contains no Owner scope. R10C carries Owner scope only from the
   exact R9B encrypted key-custody receipt and requires R9C/R10B signer binding.
2. A constructible R10B payload cannot authorize persistence. R10C fixes the
   candidate to non-authoritative and requires direct R10B cryptographic
   recompilation at the later write boundary.

Resolved Medium findings:

1. Public Mapping/scalar hooks could alter coordinates across validation.
   R10C uses one exact bounded JSON snapshot per public payload.
2. Candidate output could be mistaken for custody authority. All write,
   confirmation, trust-root, promotion, runtime and external flags are false.

Builder Evidence: focused R10C `12 PASS`; R9B-R10C direct `82 PASS`; TASK-029
`164 PASS`; schema mirror, JSON schema check, compile and diff-check PASS. Full
Product produced `4174 PASS / 5 SKIP / 1 FAIL`; the sole failure is unrelated
TASK-054 native Tk startup because the local Python installation lacks
`tk8.6/listbox.tcl`. It is retained as environment Evidence and the full Product
result is `NOT_CONFIRMED`, not PASS. Independent current-head review remains
required. No GO is claimed yet.

## Judge

Decision: PENDING_INDEPENDENT_DEV4_REVIEW.
