# TASK-029 R10A Knowledge Pack Promotion Preflight - Design / Review

Date: `2026-08-26`
Profile: `DEV-4 FOUNDATION CRITICAL`
State: `BUILDER_IMPLEMENTED_REVIEW_PENDING`

## Goal

Bind exact R6/R7/R8 compile truth, a body-free R9A verification receipt and a
terminal R9D journal receipt into one immutable, body-free promotion intent.
The intent is preparation Evidence only. It does not write or promote a Pack.

## Inputs

- exact R8 signature request plus its complete compile kwargs;
- exact R9A verification receipt;
- exact terminal `SIGNED_AND_VERIFIED` R9D journal receipt;
- stable intent ID and positive creation timestamp.

R8 recompilation transitively revalidates R6 promotion Evidence and R7
Human/Critic review binding. R9A coordinates must match the exact R8 request.
R9D must bind both the exact request hash and exact R9A receipt hash.

## Output contract

The immutable projection binds:

- Pack ID/version and predecessor Pack hash;
- exact signing candidate, request and message hashes;
- trusted signer policy and signer key hashes;
- detached signature digest, R9A receipt, R9D journal and ceremony hashes;
- predecessor as the only possible rollback target;
- initial versus replacement preflight state.

The projection explicitly requires a later Human promotion confirmation,
canonical store transaction, runtime compatibility validation and signature
artifact. The signature artifact is not present in R10A, so execution remains
blocked.

Builder self-review found that the body-free R9A and R9D dataclasses are
publicly constructible. Cross-coordinate validation detects drift but cannot
authenticate that cryptography actually produced a consistent receipt. R10A
therefore records the upstream verification claim while fixing signature
origin authentication, signature verification and promotion-confirmation
eligibility to false.

## Failure modes

- source/compiler drift: reject before projection;
- coordinate-mismatched R9A receipt: reject;
- coordinate-consistent constructible receipt: never elevate to verified;
- nonterminal or mismatched R9D receipt: reject;
- predecessor/rollback mismatch: reject;
- unknown fields, flag escalation, hash tamper or boolean timestamp: reject;
- key/signature bodies, paths, media or text: absent from the API and output.

## Authority boundary

R10A performs no filesystem, network, crypto, key-store, Provider, Timeline,
Resolve, release, deploy or Production operation. All write, promotion,
automatic promotion, runtime apply, rollback execution, release and external
effect flags remain false.
The projection is not promotion-ready and does not claim authenticated
cryptographic origin.

R10B or later must separately define explicit Human confirmation, canonical
handle-bound storage, signature artifact custody, monotonic predecessor chain,
runtime compatibility admission, recovery and rollback execution. This design
does not authorize those effects.

## Verification plan

1. exact R6-R9D synthetic Evidence compilation;
2. public schema and package mirror validation;
3. body-free and effect-false assertions;
4. source drift, coordinate mismatch and nonterminal/mismatched R9D negatives;
5. predecessor/rollback invariant and projection tamper negatives;
6. focused R10A, direct R8-R10A and TASK-029 regression;
7. independent Critic/Tester/Judge before Technical GO;
8. hosted checks on the exact immutable head.
