# TASK-058 — Montage Learning Bridge

Status: `ACTIVE — P0 HOSTED CLOSED / P1A RECEIPT CONTRACT IN PROGRESS`

## Objective

Provide a bounded, review-first bridge for two montage-learning inputs without
creating a second canonical timeline or automatic learning authority:

1. an exact BAI VIDEO PRODUCTION proposal → approved plan → human edit evidence
   lineage; and
2. a generic `bvp-montage-learning-adapter` learning export.

## P0 Atomic Unit

P0 freezes JSON contracts and deterministic validation only. The unit is
classified `DEV-4` because it is a cross-project contract and authority
boundary.

P0 uses the execution classification `NO_EXTERNAL_OR_MUTABLE_I/O`. It may
perform deterministic, read-only loading of packaged immutable JSON Schemas
through the existing TASK-055 parser. It does not read external mutable files,
write a filesystem or store, access network/database/media, start Resolve or
another native application, or call a paid provider.

The P0 completion scope contains exactly eight files: seven Builder-owned
contract/design/schema/source files and one independent Tester-owned focused
test file. The Builder does not author or modify that test file.

## P0 outputs

- Exact delivery validation can reach only `EXACT_LINEAGE_VERIFIED`.
- Generic delivery validation remains `OWNER_SCOPE_UNBOUND` and
  `REVIEW_REQUIRED`.
- A source runtime `PASS` is accepted only with executed evidence plus a
  reference, and is down-scoped to a non-authoritative observation.
- No result means `ACCEPTED`, canonical admission, timeline mutation, store
  write, learning promotion, runtime proof, or receipt issuance.

## Dependencies

- TASK-055 owns the canonical montage proposal, approved-plan, and human-edit
  evidence schemas and lineage admission.
- TASK-029 owns the Product montage timeline and remains unchanged.
- `bvp-montage-learning-adapter` owns the generic export shape; BVP independently
  revalidates its semantics before exposing a review candidate.

## Prohibited in P0

- canonical learning store or automatic promotion;
- canonical timeline ownership or mutation;
- Resolve/native/provider/paid execution;
- external connector or folder watcher;
- v1 terminal or v2 review receipt minting;
- changes to CHANGELOG, current state, task index, TASK-029, or active locks.

## Completion gate

P0 is complete only after schema mirrors are byte-identical, focused static and
contract tests pass, independent Tester/Critic/Judge responsibilities report no
unresolved Critical/High finding, and the exact eight-file scope is clean.

P1/P2 connector, queue, UI review, store, or receipt work requires a separate
authorized Atomic Unit. P0 does not imply that authority.

## P0 hosted closure

- target PR: `#341`
- target merge: `1af0a342730a45168d615fdbc689a251dbe52a25`
- CHANGELOG lock closure PR: `#346`
- closure merge: `d4257b11ee071cc562107e4b71dacb8bb45cd11f`
- registry revision: `82`
- hosted and post-main checks: `PASS`
- immutable P0 blobs: `8 / 8 preserved`

## P1A Atomic Unit

P1A freezes the pure `BvpMontageLearningAdmissionReceipt/v2` read contract and
the deterministic idempotency binding required by the later importer. It is a
DEV-4 `NO_EXTERNAL_OR_MUTABLE_I/O` unit.

P1A validates caller-supplied receipt structures, canonical self-hashes,
source identity, Owner scope, state combinations, duplicate reference shape,
and canonical-store commit claim shape. Duplicate lineage and store commit
remain unverified in P1A and are projected as such. P1A does not mint, persist,
publish, or recover a receipt and does not verify that a caller is the BVP
receipt authority.

The P1A completion scope contains exactly six files: this task record, one
detailed design, one public schema and its byte-identical packaged mirror, one
pure source module, and one focused test module.

### P1A prohibited effects

- filesystem bridge creation, scan, claim, move, write, replace, or recovery;
- canonical learning store read/write or TASK-029 admission;
- queue, importer, connector, watcher, UI, installer, or capability handshake;
- receipt minting or origin-authority verification;
- Timeline, Resolve, native, provider, network, database, Release, Deploy, or
  Production effects;
- CHANGELOG, active-lock Registry, current-state, task-index, or TASK-029
  mutation.

P1B/P1C filesystem store, CAS/recovery, importer classification, Human binding,
and actual receipt issuance require separate bounded designs after P1A is
hosted and fresh-main green.
