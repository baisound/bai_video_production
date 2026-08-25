# TASK-058 — Montage Learning Bridge

Status: `ACTIVE — P0 CONTRACT FREEZE UNDER REVIEW`

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
