# TASK-029 R10B Trusted Signature Admission — Design / Critic / Judge

Date: 2026-08-27

Status: IMPLEMENTATION_REVIEW_PENDING

DEV profile: DEV-4 FOUNDATION CRITICAL

## Atomic Unit

R10B closes one narrow gap left explicit by R10A: an R9A verification receipt
is a public constructible body-free value and therefore cannot prove that the
Ed25519 verifier ran. R10B re-runs the R9A verifier in the current
function call and requires its exact output to reproduce the R10A verification
claim and the R9D journal binding.

Allowed paths are this design, the TASK-029 task record, one new public schema
and package mirror, one new Product module and one focused test module.
CHANGELOG.md, ACTIVE-WORK-LOCKS.json, canonical stores, installers, UI, Resolve,
Timeline, runtime Profile application and release paths are outside this Unit.

## Inputs and algorithm

1. Require the R10A intent, R10A compile arguments, R9C ceremony receipt and
   signer policy payload to use exact public boundary types.
2. Copy every public JSON input once into a recursively exact, cycle/depth/node
   bounded built-in snapshot before parsing. Rebuild the nested R6-R8 compile
   tree only from an explicit allowlist of exact Product enums and frozen
   dataclasses; subclasses, custom Mapping hooks and concurrent mutation cannot
   enter the snapshot.
3. Execute `verify_detached_knowledge_pack_signature` directly with the exact
   request snapshot, supplied policy, transient raw Ed25519 public key and
   detached signature.
4. Require the newly produced verification receipt to equal the R10A claimed
   verification receipt byte-for-byte at the canonical-dict level.
5. Recompile R10A using that verified result and require the supplied R10A intent
   to equal the exact recompiled projection.
6. Parse and cross-bind the exact R9C ceremony and terminal R9D journal to the
   request, signer, detached-signature and verification receipt, then require
   verification time to be at or after the R10A, R9C and R9D terminal times.
7. Return a body-free in-memory admission binding Pack, predecessor, signer,
   request, message, signature digest, verification, journal and ceremony.

The raw public key and signature are not returned or persisted. Private key
material is never accepted.

## Authority boundary

The admission states only that the R9A verifier executed in the current call
and mathematically verified the signature against the caller-supplied,
self-validating policy. R10B has no canonical Owner trust-root, latest policy
reader or Owner binding. Therefore canonical/latest source revalidation,
canonical signer-origin authentication, canonical trusted-policy revalidation
and Owner signer binding are machine-readable false. Its dataclass and JSON
projection remain publicly constructible, so the standalone payload is
explicitly non-authoritative and every downstream consumer must direct-recompile
with the artifact again.

R10B does not confirm signature-artifact custody, mint a canonical receipt,
make Human promotion confirmation eligible, write or promote a Knowledge Pack,
apply a runtime Profile, execute rollback, or authorize Timeline, Resolve,
Release, Deploy or Production effects.

## Failure model

- invalid, wrong-length or different public key/signature: fail closed;
- revoked, tampered or nonmatching signer policy: fail closed;
- forged constructible R9A claim: fail closed unless current-call verification
  reproduces it and R9D binds that exact receipt;
- R10A intent/source drift: fail closed;
- R9C/R9D coordinate drift or verification before the intent/ceremony/journal
  causal floor: fail closed;
- custom/stateful public Mapping: reject without invoking its hooks;
- concurrent mutation after request snapshot: cannot switch the verified
  request;
- unknown fields, effect-flag changes, identity/hash changes: fail closed;
- artifact custody, canonical persistence and downstream provenance: remain
  NOT_CONFIRMED.

## Verification plan

- strict schema and package-mirror validation;
- valid synthetic Ed25519 direct verification and body/secret absence;
- signature, public-key, policy, intent, ceremony and journal negative tests;
- nested stateful Mapping, public parser/verifier hook and concurrent mutation
  tests;
- intent/R9C/R9D time-causality negative tests;
- output tamper, unknown field, bool/time and replacement-lineage tests;
- focused R10B, direct R8-R10B/TASK-029 and full Product regression;
- diff/exact-path review and independent DEV-4 Critic/Tester/Judge.

## Critic / Judge record

Initial Builder threat review identifies the constructible-receipt provenance
gap, mutable Mapping double-read risk and standalone-output overclaim as the
three primary failure modes. First independent review was Technical NO-GO with
C/H/M/L `0/2/2/0`: missing R9C/R9D time causality, canonical trust-root
overclaim, shallow nested snapshots and public Mapping hook execution. The
bounded rework adds exact ceremony/journal causality, supplied-policy-only
claims, explicit exact-type deep snapshots and hook-free public admission
parsing. Independent re-review and final Judge status are pending current-head
validation; no GO is claimed in this section yet.

Builder rework validation: focused R10B `19 PASS`, TASK-029 `151 PASS`, full
Product `4162 PASS / 6 SKIP / 0 FAIL`, schema/package mirror, compile and
diff-check PASS. These results are Evidence only; independent current-head
Critic/Tester/Judge remains required.
