# TASK-029 R7 Knowledge Pack Signing Candidate — Design / Critic / Judge

Date: 2026-08-25

Governance: DEV-4 PRIVACY, LEARNING AND RELEASE INTEGRITY

Atomic Unit: exact R6 candidate plus independent Human/Critic review binding

## Goal

Recompile one R6 Knowledge Pack promotion candidate from its exact current R5/R1/R0 sources and bind it to a separate explicit Human review and a later independent Critic review. Emit a body-free, immutable in-memory candidate that is eligible only for a future external-signature gate.

This Unit does not create a Knowledge Pack, use or accept a signing key, create or verify a signature, write Git or another store, promote knowledge, apply a runtime Profile, execute rollback, release, deploy, or produce any external effect.

## Inputs

- exact serialized R6 candidate;
- R6 candidate ID, feature key, sources and policy required to regenerate it;
- explicit Human review bound to the exact R6 candidate hash;
- independent Critic review bound to the same exact candidate hash;
- body-free reviewer coordinates, reason codes and review timestamps;
- intended Pack ID/version and optional predecessor Pack hash.

## Rules

1. R6 is recompiled on every call and the supplied payload must match byte-semantically.
2. R6 state must be `READY_FOR_HUMAN_KNOWLEDGE_PACK_REVIEW`.
3. Human and Critic review IDs and reviewer coordinates must be distinct.
4. Critic review time must be strictly later than Human review time.
5. Critic acceptance requires zero unresolved Critical and High findings.
6. Human rejection and Critic rejection remain distinct terminal candidate states.
7. The output omits Owner, Project and reviewer coordinates and retains only exact review hashes.
8. Signature/key/write/promotion/apply/rollback/release/external-effect flags remain false.

## Output states

- `READY_FOR_EXTERNAL_SIGNATURE`
- `HUMAN_REJECTED`
- `CRITIC_REJECTED`

`READY_FOR_EXTERNAL_SIGNATURE` means only that source and reviews are coherently bound. It is not a signature, Pack, release, promotion, runtime, or rollback authority.

## Failure modes

- source candidate or latest-source drift;
- candidate not review-ready;
- review hash/candidate binding mismatch;
- duplicate review identity or same reviewer coordinate;
- Critic review not later than Human review;
- Critic acceptance with unresolved Critical/High findings;
- unknown fields, malformed IDs/hashes/version, schema drift, or authorization flag mutation.

All structural and lineage failures raise `ValueError`; they are not converted into a promotable state.

## Critic review

Finding 1: an independent Critic record could be supplied by the same reviewer under a second review ID.

Resolution: reviewer coordinates must differ in addition to review IDs.

Finding 2: a Critic record could predate the Human review and still appear independent.

Resolution: Critic time must be strictly later than Human time; focused negative coverage is included.

Finding 3: “signing candidate” could be mistaken for a signed Pack or signing authority.

Resolution: the output has `signature_present=false`, `signature_verified=false`, `signing_key_material_included=false`, `external_signature_required=true`, and no I/O or cryptographic signing surface.

Finding 4: review or R6 payload tampering could survive if only IDs were compared.

Resolution: R6 is regenerated from exact current sources, both reviews bind its full canonical hash, and the final verifier recompiles the complete result.

Residual Critical/High/Medium findings: 0 / 0 / 0.

## Tester evidence

- ready/no-effect/privacy/schema case;
- deterministic review/candidate round-trip and exact verifier;
- source/candidate/final payload tamper rejection;
- Human and Critic rejection state separation;
- unresolved Critical/High acceptance rejection;
- reviewer identity/coordinate independence;
- Critic-after-Human ordering;
- immutability, schema mirror identity and no-I/O/static import boundary.

## Judge

Decision: ACCEPT R7 IMPLEMENTATION FOR HOSTED REVIEW.

Reason: the Unit closes the review-binding gap between R6 and a future signing gate without implementing or authorizing signature, Pack write, promotion, runtime apply, rollback, Release, Deploy, or Production effects.

Next boundary: a future Unit may verify an externally supplied signature and construct a versioned Pack only under a separate design and authority. Automatic promotion and runtime application remain separately denied.
