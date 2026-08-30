# TASK-058 P1C-B Durable Staging Read-back Design

Date: 2026-08-26
Status: IMPLEMENTATION BOUND
DEV profile: DEV-4 FOUNDATION CRITICAL
Owner: Product Development 2 / TASK-058

## 1. Goal

P1C-B closes two narrow gaps left by P1C-A without creating canonical
admission authority:

1. recompile one exact TASK-055 delivery from its raw built-in JSON body; and
2. prove that the resulting exact P1B entry is present in the P1B staging
   ledger bytes read through one pinned file handle.

The result is a body-free
`NONAUTHORITATIVE_DURABLE_STAGING_READBACK_PROJECTION`. It is a point-in-time
observation only.

## 2. Inputs and trust boundary

The production entrypoint accepts:

- one raw exact delivery;
- an absolute Product Project root;
- the expected P1B `store_id`, Owner scope, revision, and entry digest.

The entrypoint snapshots only exact built-in JSON values. It does not accept a
serialized P1C-A projection as source evidence. It obtains the staged entry
from the pinned ledger bytes and invokes the P1C-A compiler with the raw
delivery plus that entry.

Public construction of the projection is not exposed. The live object and a
JSON document conforming to the public Schema are diagnostic data only; neither
is an admission capability. P1C-C or later must invoke this verifier internally
from raw delivery and expected staging coordinates and must never accept a
caller-supplied live or serialized projection as verification input.

## 3. Handle-bound read

The reader derives only the fixed P1B relative path
`state/montage-learning-admission-staging-ledger.json`.

- POSIX opens the Project root, `state`, and ledger with relative descriptor
  operations and `O_NOFOLLOW`; it requires regular-file identity and stable
  size/mtime/ctime across the bounded read.
- Windows opens root, state, and ledger with non-inheritable Win32 handles and
  `FILE_FLAG_OPEN_REPARSE_POINT`; it rejects reparse points, checks final
  handle paths and file IDs, and denies write/delete sharing while reading the
  ledger.
- Both paths reject missing, empty, oversized, non-canonical, duplicate-key,
  malformed, or hash-invalid JSON. The exact P1B ledger parser remains the
  schema/hash-chain authority.
- All opened handles are closed on success and failure. Close failure is a
  failed read-back, not PASS.

The returned file identity is domain-hashed. No host path, device identifier,
inode, Windows volume serial, or file ID is published.

## 4. Exact verification

P1C-B requires all of the following in the same invocation:

- exact P1B store identity, Owner scope, and revision;
- exactly one entry matching the expected entry digest;
- P1C-A recompilation from the raw delivery and the handle-read entry;
- equality of Project, source, proposal, approved-plan, Evidence,
  idempotency, Human-binding, and entry coordinates;
- preservation of `DELETED` as negative feedback.

The projection carries no reusable runtime capability marker. Its true
observation fields describe only this completed invocation; downstream effects
must not trust or rehydrate the projection and must rerun this verifier inside
their own trusted operation.

## 5. Claims deliberately left false

P1C-B does not prove who originally wrote the P1B file. It proves the exact
path/file identity observed through the open handle and membership in the
validated P1B ledger. Therefore these remain false:

- source-lineage origin and Human-binding actor origin;
- staging writer/store origin;
- Product Project root canonical ownership;
- hostile ancestor namespace race protection;
- post-return state stability;
- monotonic Project anchor and rollback detection;
- canonical store write/commit and public receipt mint;
- canonical admission or automatic learning promotion;
- Timeline, Resolve, external, Release, Deploy, or Production authority.

P1C-C or later must provide a handle-bound writer, external monotonic anchor,
atomic canonical promotion/recovery, and typed public receipt before any of
those claims can change.

## 6. Exact scope

The Atomic Unit changes exactly six files:

1. `docs/ai-team/tasks/TASK-058/task.md`;
2. this design;
3. public JSON Schema;
4. byte-identical packaged Schema mirror;
5. one bounded reader module; and
6. one focused fault/boundary test module.

It must not modify P1B/P1C-A source, CHANGELOG, active-lock Registry,
current-state, task-index, TASK-029, Product Project data, or shared runtime
paths.

## 7. Acceptance

- Schema Draft 2020-12 and mirror parity pass.
- Windows and POSIX handle paths are statically covered; the host-native path
  is exercised with real temporary files.
- raw delivery, store/scope/revision/entry, JSON/hash-chain, reparse/symlink,
  size, identity drift, read, and close failures fail closed.
- live or serialized projections remain diagnostic-only and cannot replace an internal raw-verifier rerun.
- focused P1C-B and related P0/P1A/P1B/P1C-A regressions pass.
- independent Critic, Tester, and Final Judge report zero unresolved Critical,
  High, Medium, or Low findings.
