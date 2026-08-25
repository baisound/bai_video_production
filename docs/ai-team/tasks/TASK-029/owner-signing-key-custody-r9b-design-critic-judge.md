# TASK-029 R9B — Owner Signing Key Custody Design / Critic / Judge

Date: 2026-08-26
Governance: DEV-4 PRIVACY, LEARNING AND RELEASE INTEGRITY
Unit: R9B Owner-local DPAPI private-key custody

## Goal

R9B adds the smallest durable boundary needed before a real Owner Ed25519 key can be used by BVP. A raw 32-byte Ed25519 seed is admitted only once after an explicit Human confirmation bound to the exact custody ID, Owner-scope SHA-256, and public-key-derived signer key ID.

## Contract

- Default encryption is Windows Current User DPAPI.
- The DPAPI entropy domain is unique to R9B and is not shared with Owner Decision or Owner Profile stores.
- The disk document contains only versioned ciphertext and integrity metadata.
- The decrypted secret validates the Ed25519 private/public relationship and the signer key ID.
- The public read boundary returns a body-free custody receipt.
- The target path is protected by a cross-process exclusive lock and atomic validated replace.
- Existing custody is immutable: overwrite, replacement, rotation, and replay are rejected.
- Wrong cipher, malformed plaintext, checksum drift, secret drift, mismatched confirmation, symlink, and interrupted write fail closed.

## Authority boundary

R9B authorizes exactly one encrypted custody write after explicit Human confirmation. It does not provide a signing API or a private-key export API. It does not authorize Knowledge Pack write/promotion, automatic promotion, runtime Profile apply, rollback execution, Release, Deploy, Production activation, Resolve/Timeline mutation, provider calls, or Cloud effects.

PuTTY PPK parsing, OpenSSH conversion, real key generation, passphrase custody, and native import are not implemented by this source Unit. Those actions require the separately recorded sleep-window authority and the execution runbook. Tests use newly generated synthetic keys only and never persist or print a real Owner secret.

## Schema

The public and package-mirror Schema describe only the encrypted outer envelope:

- schema and record identity
- cipher suite
- base64 ciphertext
- ciphertext SHA-256
- explicit false plaintext marker
- whole-document SHA-256

Secret fields are intentionally excluded from the public Schema.

## Failure modes

| Failure | Required result |
|---|---|
| Human confirmation absent or mismatched | reject before write |
| seed is not exactly 32 bytes | reject before write |
| derived public key differs | reject |
| existing custody path | reject; never overwrite |
| symlink target | reject |
| wrong cipher / ciphertext tamper | integrity error |
| decrypted record/hash/key-pair drift | integrity error |
| failure before atomic replace | no target file |
| receipt parser receives key body or unknown fields | reject |

## Critic

The implementation was reviewed against R9A verification, existing TASK-029 DPAPI stores, atomic writer semantics, and the R9A PuTTYgen runbook boundary.

Findings:

- Critical: 0
- High: 0
- Medium: 0
- Low: 0

The store intentionally has no sign/export/generate method and no network or subprocess dependency. A real key is not test material.

## Tester evidence

- focused R9B: 13 PASS
- Windows Current User DPAPI synthetic round-trip: PASS
- schema mirror and strict validation: PASS
- tamper, wrong cipher, plaintext, symlink, one-shot overwrite, and atomic-failure negative tests: PASS

- TASK-029 direct regression: 94 PASS
- full Product regression: 3865 PASS / 6 SKIP / 0 FAIL
- independent hosted review: PENDING

## Judge

Decision: GO for bounded R9B source integration after required regression and release-metadata transaction.

This GO does not authorize real signing, Knowledge Pack mutation, Release, Deploy, or Production. Native PuTTYgen activity remains separately evidenced and may occur only while the current sleep-window authority remains active.
