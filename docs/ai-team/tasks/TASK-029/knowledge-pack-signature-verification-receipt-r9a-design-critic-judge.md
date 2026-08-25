# TASK-029 R9A Knowledge Pack Signature Verification Receipt Design

Date: 2026-08-26
Status: IMPLEMENTED_LOCAL_PENDING_INDEPENDENT_REVIEW_AND_HOSTING
Authority: Owner explicit approval in the active development thread on 2026-08-26
Governance: DEV-4 PRIVACY, LEARNING AND RELEASE INTEGRITY

## Atomic Unit

R9A consumes an exact, currently revalidated R8 signature request plus a canonical trusted signer policy, one raw Ed25519 public key and one detached signature. It verifies only the R8 versioned signature input bytes and emits an immutable body-free verification receipt.

The exact signed bytes remain the ASCII bytes of the sha256-prefixed signature_message_sha256 value required by R8.

## Trust binding

- The full trusted signer policy is canonical-hashed and must equal the policy SHA bound by R8.
- The raw 32-byte public key SHA-256 is the signer key ID and must equal the key ID bound by R8.
- The key ID must appear exactly once in the active trusted policy.
- The R8 request is recompiled from its exact R7 sources before cryptographic verification.
- Only Ed25519 and a 64-byte detached signature are accepted.

## Receipt boundary

The receipt retains request, candidate, Pack, policy, key, message and detached-signature SHA coordinates. It does not retain signature bytes, public-key material, private-key material, credentials or host paths.

VERIFIED means only that the supplied detached signature matched the exact R8 bytes under the allowed public key after current-source revalidation. It does not authorize Knowledge Pack write or promotion, automatic promotion, runtime Profile apply, rollback, Release, Deploy or any external effect.

## Failure modes

Fail closed on:

- R8 source drift or request tamper
- policy hash drift, revoked policy, duplicate or unsorted key IDs
- public key identity mismatch or untrusted key
- malformed public key or signature length
- invalid detached signature
- receipt field, authority flag or receipt hash tamper
- unknown Schema fields

Errors do not expose public key or signature bodies.

## Dependency decision

Use the maintained cryptography package instead of implementing Ed25519 primitives locally. Project range is cryptography version 46 or newer and lower than 51. Python 3.11 through 3.13 remain within the package-supported range. The development environment observed version 50.0.0.

## Explicit exclusions

- real Owner private-key generation or storage
- DPAPI key vault
- signing command or signing service
- filesystem/network/key-store access
- real Knowledge Pack signature
- Pack write, promotion, apply or rollback
- Release, Deploy or Production effect

Those actions require later bounded Units. R9B will design and implement Owner-local DPAPI private-key custody without creating the real key until its native execution gate is satisfied.

## Verification

Required before commit-ready:

- canonical Policy and Receipt Schema validation
- package mirror byte identity
- valid Ed25519 round trip using synthetic ephemeral test keys
- signature/public-key/policy/request/receipt tamper matrix
- revoked policy, duplicate key and length rejection
- no private-key generation or I/O imports in Product source
- R8/R9 direct regression
- TASK-019/TASK-029 targeted regression
- dependency and diff/scope checks

No native key store, real private key or real Pack is used by these tests.

## Critic review

- High: A hash-only key coordinate could be mistaken for trust. Resolved by requiring the raw public key digest to equal the R8 key ID and requiring that ID in the exact active policy whose canonical SHA is bound by R8.
- High: VERIFIED could be mistaken for Pack promotion authority. Resolved by fixing every write, promotion, runtime apply, rollback, release and external-effect flag to false in both implementation and Schema.
- High: A stale R8 request could be verified after source drift. Resolved by exact R7/R8 recompilation before the cryptographic call and by recording latest_source_revalidated=true.
- Medium: Local Ed25519 implementation would create avoidable cryptographic risk. Resolved by using the maintained cryptography primitive and pinning a bounded supported range.
- Medium: Signature or public-key bodies could leak through the receipt. Resolved by retaining SHA coordinates only and by using body-free errors.

Residual Critical/High/Medium: 0/0/0.

## Tester results

- R9A focused plus R8 request regression: 13 PASS
- TASK-019/TASK-029 targeted regression: 99 PASS
- Full Product regression: 3852 PASS / 6 SKIP / 0 FAIL
- pyproject TOML parse: PASS
- Python compile: PASS
- pip dependency check: PASS
- Schema JSON and canonical/package mirror byte identity: PASS
- diff whitespace check: PASS

The six skips are pre-existing platform or live-process gates: POSIX inode/descriptor/directory-fsync cases, non-Windows credential-vault contract and a running OBS installer fail-closed case. No R9A test was skipped.

## Judge decision

ACCEPTED_LOCAL_PENDING_HOSTED_INTEGRATION.

R9A satisfies the bounded approved cryptographic-verification Unit. It does not generate or store an Owner private key and cannot sign, write or promote a Knowledge Pack. Hosted CI/Security and the exact CHANGELOG transaction remain pending. Independent hosted checks will provide the external execution gate before merge.
