# TASK-058 — Montage Learning Bridge

Status: ACTIVE — P0/P1A/P1B/P1C-A HOSTED CLOSED / P1C-B IMPLEMENTATION IN PROGRESS

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

## P1A local completion checkpoint

- fresh-main composition HEAD: `5d94f06825062afd6fa73403fb04c94e3956691e`
- exact scope: `6 / 6`
- focused tests: `32 / 32 PASS`
- P0/TASK-055 related regression: `57 / 57 PASS`
- custom JSON-like TOCTOU matrix: `11 / 11 PASS`, hook invocation `0`
- schema Draft 2020-12, packaged mirror, fixed vectors, compile, and diff:
  `PASS`
- independent Tester, Critic, and final Judge: `GO`
- unresolved Critical/High findings: `0 / 0`
- filesystem/store/importer/native/provider/paid/Release/Deploy/Production
  effects: `NOT EXECUTED`

P1A remains hosting-pending until its dedicated CHANGELOG lock transaction,
hosted checks, merge, post-main checks, and closure read-back are complete.

## P1A hosted closure

- target PR: #351
- target merge: f524781b88fafb469b55f7853976ebd73ec3c1bd
- CHANGELOG lock closure PR: #356
- closure merge: 85ddb70601898046826f869a9a9a1f2856ebdfb3
- registry revision: 86
- hosted and post-main checks: PASS
- immutable P1A blobs: 6 / 6 preserved

## P1B Atomic Unit

P1B adds a BVP-owned, body-free admission staging ledger. The ledger provides
an in-file hash chain, optimistic CAS, exact duplicate read-back, collision
rejection, atomic replacement, and restart read-back. It accepts only claimed
P0 exact-profile coordinates and never accepts the generic SKILL profile.

P1B is a DEV-4 filesystem/state-machine unit. It stores identifiers, digests,
timestamps, and explicit false authority flags only. It does not store proposal,
plan, evidence, actor, account, transcript, media, path, or secret bodies.
P1B does not verify P0 source origin, Human-binding origin, monotonic head, or
rollback resistance and does not create a canonical store commit. P1C must
revalidate the source, verify the exact Human binding, establish an external
monotonic anchor, and atomically promote before any public receipt can claim a
canonical store commit.
P1B's exact path security model is COOPERATIVE_LOCAL_WRITER_ONLY. Its path
checks reject pre-existing and observed unsafe paths, but hostile concurrent
junction/reparse replacement protection is NOT_CONFIRMED. P1C must use a
handle-bound writer for canonical promotion; the P1B staging writer and
external_effect_authorized=false flag are not filesystem-race security proof.


The P1B completion scope contains exactly six files: this task record, one
detailed design, one public schema and its byte-identical packaged mirror, one
store module, and one focused fault/recovery test module.

### P1B prohibited effects

- importer scan/claim/move/quarantine, connector, watcher, queue, UI, installer,
  or capability handshake;
- Generic observation canonical admission or automatic promotion;
- Human binding creation/verification and public receipt mint/publication;
- Timeline, Resolve, native, provider, network, database, Release, Deploy, or
  Production effects;
- real Product Project/store mutation outside isolated tests;
- CHANGELOG, active-lock Registry, current-state, task-index, or TASK-029
  mutation before a separate hosted integration lock.

P1C remains responsible for importer classification, exact Human binding
verification, durable staging membership/store-origin verification, monotonic
Project binding, canonical promotion, and public v2 receipt issuance/recovery.
A P1B staging digest cannot be used as canonical_store_commit_sha256.

## P1B local completion checkpoint

- fresh-main composition HEAD: e22945635abc398d102283b11598bd1452eb196c
- exact scope: 6 / 6
- schema Draft 2020-12 and packaged byte-identical mirror: PASS
- compile and diff check: PASS
- focused fault/recovery tests: 28 / 28 PASS
- related TASK-058/TASK-055/atomic regression: 119 / 119 PASS
- independent path-security delta observations: 9 / 9 PASS
- full repository regression: 3927 PASS / 6 SKIPPED / 2 WARNINGS
- final Judge: GO
- independent Tester and Critic: GO
- unresolved Critical/High/Medium/Low findings: 0 / 0 / 0 / 0
- hostile path-race protection, directory durability, P1C handle-bound
  canonical promotion implementation/execution: NOT_CONFIRMED
- Product Project, canonical store, receipt, Timeline, Resolve, native,
  provider, network, paid, Release, Deploy, and Production effects:
  NOT EXECUTED

## P1B hosted closure

- target PR: #361
- target merge: 423fc827a62510c39b702e47814ba23178a395c5
- CHANGELOG lock closure PR: #365
- closure merge: 38c9364f00750db7f33c7ee779f2f3ab05a7e344
- registry revision: 92
- hosted and post-main checks: PASS
- immutable P1B blobs: 6 / 6 preserved

## P1C-A Atomic Unit

P1C-A is the validation-only source/Human-binding preflight slice of P1C. It snapshots
one untrusted exact delivery and one caller-supplied P1B staging entry as JSON,
reruns the P0/TASK-055 exact lineage admission, rejects `do_not_learn`, derives
a stable canonical Evidence ID, recomputes a domain-separated Human binding,
and requires every entry coordinate to match before returning a body-free
`NONAUTHORITATIVE_SOURCE_HUMAN_PREFLIGHT_PROJECTION`. Its public constructor and
parser prove self-consistency only; compiler execution, source/Human origin, entry
origin, durable ledger membership, and store origin remain false.

Deleted Human edits remain eligible as explicit negative feedback when their
exact TASK-055 lineage is valid and `do_not_learn=false`; P1C-A does not
rewrite or erase the source Evidence. Generic SKILL observations cannot enter
this preflight.

P1C-A is DEV-4 `NO_MUTABLE_OR_EXTERNAL_I/O`; the existing TASK-055 validator
may lazily read only packaged immutable Schemas. Its result fixes staging
membership/store origin, monotonic Project anchor, rollback detection, canonical
store write/commit, receipt mint, canonical admission, automatic promotion,
Timeline, Resolve, and external effect flags to false. P1C-B or later remains
responsible for recompile from raw delivery plus handle-bound durable staging
readback, staging membership/store-origin verification, the handle-bound writer,
monotonic Project anchor, canonical promotion transaction, recovery, and public
v2 receipt issuance. A serialized P1C-A projection or `from_dict()` result alone
must never be admitted.

The P1C-A exact scope is six files: this task record, one detailed design, one
public Schema and byte-identical packaged mirror, one bounded source module, and
one focused test module. `CHANGELOG.md`, active locks, current state, task
index, TASK-029, P0/P1A/P1B source/schema/test, and Product Project data are
outside this source Unit.

## P1C-A local completion checkpoint

- source implementation commit: `4aab2a4697d072841af58ecf19f7e2a12c0849db`;
- fresh origin/main integrated: `fc9398950b07759f82b91801f76f9f3eea195462`;
- composition HEAD before this Evidence-only commit: `50e1114b9a969f507df82bb72eef64c85f16634e`;
- exact Product delta: 6 / 6 files;
- focused P1C-A tests: 21 / 21 PASS;
- related P0/P1A/P1B/TASK-055 regression: 138 / 138 PASS;
- fresh-main full Product regression: 4093 PASS / 6 SKIPPED / 2 WARNINGS;
- Schema Draft 2020-12 and packaged byte identity: PASS;
- Schema SHA-256: `759DDAD24A53D46B8DA3286229D6EF26572587806BE6F3FC08E3FCD43EFF8011`;
- independent Critic and Tester: GO;
- final Judge: GO;
- unresolved Critical/High/Medium/Low findings: 0 / 0 / 0 / 0;
- durable staging membership/store origin, monotonic Project anchor, canonical
  promotion/recovery, receipt issuance, Timeline/Resolve/native/provider effects:
  NOT IMPLEMENTED / NOT EXECUTED.
## P1C-B Atomic Unit

P1C-B is the durable staging read-back slice of P1C. It snapshots one raw
exact TASK-055 delivery, opens the fixed P1B staging ledger through pinned,
non-inheritable handles, validates exact canonical ledger bytes and the full
P1B hash chain, locates one expected entry digest, and reruns the P1C-A
compiler against that handle-read entry. The body-free output is
`NONAUTHORITATIVE_DURABLE_STAGING_READBACK_PROJECTION` and carries a private
process-local runtime marker that serialized mappings cannot recreate.

P1C-B proves point-in-time raw recompilation, pinned-file read, fixed staging
path identity, and exact ledger membership only. It does not prove the writer
or staging-store origin, Product Project root canonical ownership, hostile
ancestor namespace race protection, or post-return state. Source/Human actor
origin, monotonic Project anchor, rollback detection, canonical promotion,
receipt mint, canonical admission, automatic promotion, Timeline, Resolve, and
external effects remain false.

The P1C-B exact scope is six files: this task record, one detailed design, one
public Schema and byte-identical packaged mirror, one bounded reader module,
and one focused fault/boundary test module. P1B/P1C-A source, CHANGELOG, active
locks, current state, task index, TASK-029, and Product Project data are outside
this source Unit. P1C-C or later remains responsible for handle-bound writing,
external monotonic anchoring, canonical promotion/recovery, and public v2
receipt issuance.
