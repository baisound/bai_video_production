# TASK-029 R10B Trusted Signature Admission — Design / Critic / Judge

Date: 2026-08-27

Status: IMPLEMENTATION_REVIEW_PENDING

DEV profile: DEV-4 FOUNDATION CRITICAL

## Atomic Unit

R10B closes one narrow gap left explicit by R10A: an R9A verification receipt
is a public constructible body-free value and therefore cannot prove that the
Ed25519 verifier ran. R10B re-runs the trusted R9A verifier in the current
function call and requires its exact output to reproduce the R10A verification
claim and the R9D journal binding.

Allowed paths are this design, the TASK-029 task record, one new public schema
and package mirror, one new Product module and one focused test module.
CHANGELOG.md, ACTIVE-WORK-LOCKS.json, canonical stores, installers, UI, Resolve,
Timeline, runtime Profile application and release paths are outside this Unit.

## Inputs and algorithm

1. Require the R10A intent, R10A compile arguments and signer policy payload to
   be exact built-in dictionaries at their public JSON boundaries.
2. Copy the R8 signature request, R9A claim, R9D journal receipt, R10A intent
   and trusted signer policy into hook-free snapshots before validation.
3. Execute `verify_detached_knowledge_pack_signature` directly with the exact
   request snapshot, trusted policy, transient raw Ed25519 public key and
   detached signature.
4. Require the newly produced verification receipt to equal the R10A claimed
   verification receipt byte-for-byte at the canonical-dict level.
5. Recompile R10A using that trusted result and require the supplied R10A intent
   to equal the exact recompiled projection.
6. Return a body-free in-memory admission binding Pack, predecessor, signer,
   request, message, signature digest, verification, journal and ceremony.

The raw public key and signature are not returned or persisted. Private key
material is never accepted.

## Authority boundary

The admission states only that the trusted verifier executed in the current
call. Its dataclass and JSON projection remain publicly constructible, so the
standalone payload is explicitly non-authoritative and every downstream
consumer must direct-recompile with the artifact again.

R10B does not confirm signature-artifact custody, mint a canonical receipt,
make Human promotion confirmation eligible, write or promote a Knowledge Pack,
apply a runtime Profile, execute rollback, or authorize Timeline, Resolve,
Release, Deploy or Production effects.

## Failure model

- invalid, wrong-length or different public key/signature: fail closed;
- revoked, tampered or nonmatching signer policy: fail closed;
- forged constructible R9A claim: fail closed unless trusted verification
  reproduces it and R9D binds that exact receipt;
- R10A intent/source drift: fail closed;
- custom/stateful public Mapping: reject without invoking its hooks;
- concurrent mutation after request snapshot: cannot switch the verified
  request;
- unknown fields, effect-flag changes, identity/hash changes: fail closed;
- artifact custody, canonical persistence and downstream provenance: remain
  NOT_CONFIRMED.

## Verification plan

- strict schema and package-mirror validation;
- valid synthetic Ed25519 direct verification and body/secret absence;
- signature, public-key, policy, intent and journal-claim negative tests;
- stateful Mapping and concurrent mutation tests;
- output tamper, unknown field, bool/time and replacement-lineage tests;
- focused R10B, direct R8-R10B/TASK-029 and full Product regression;
- diff/exact-path review and independent DEV-4 Critic/Tester/Judge.

## Critic / Judge record

Initial Builder threat review identifies the constructible-receipt provenance
gap, mutable Mapping double-read risk and standalone-output overclaim as the
three primary failure modes. The implementation addresses them through trusted
direct execution, hook-free snapshots and explicit downstream recompile / no
authority flags. Independent review and final Judge status are pending current
head validation; no GO is claimed in this section yet.
