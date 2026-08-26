# TASK-058 P1C-C Canonical Promotion Ledger Candidate Contract

Date: `2026-08-26`
Profile: `DEV-4 FOUNDATION CRITICAL`
Atomic Unit: `P1C-C / pure canonical promotion ledger candidate contract`
Execution class: `NO_EXTERNAL_OR_MUTABLE_I/O`

## 1. Decision

P1C-C defines the deterministic append-only ledger candidate that a later
handle-bound Product Project transaction may persist. It is deliberately not a
canonical store, writer, receipt issuer, or reusable P1C-B verification
capability. The contract copies only body-free coordinates from an exact
in-process typed `MontageLearningDurableStagingReadback` structural snapshot
and marks every output `SOURCE_REVALIDATION_REQUIRED / NOT_MINTED`. Exact
Python type identity is not source-origin authentication and cannot elevate
any authority flag.

The contract exists before the writer so the chain, CAS, duplicate, collision,
bounded-size, and serialized-authority rules are fixed independently from
filesystem and ProjectSave failure modes.

## 2. Records

### Entry candidate

One entry binds:

- Project, canonical-store, and Owner-scope coordinates;
- sequential entry revision, parent entry, and prior chain;
- source record/hash and domain-separated idempotency key;
- P1B store/revision/entry/ledger/file-identity/read-back-digest coordinates;
- canonical Evidence ID/hash and Human binding hash;
- negative-feedback preservation;
- exact false authority and effect maps;
- domain-separated entry and chain hashes.

An entry never carries proposal, approved-plan, Human-edit, transcript, media,
path, actor, account, rationale, secret, or receipt body. The P1C-B platform
security label is retained only as a closed diagnostic label. It is not writer
or Project-root origin proof.

### Ledger candidate

The ledger is keyed by `project_id + canonical_store_id + owner_scope_hash` and
contains at most 4096 entries. `ledger_revision == entry_count`; genesis uses a
fixed empty-chain digest; the latest entry and chain must match the final entry.
The ledger self-hash covers every other field. Empty and non-empty sentinels are
strict and booleans are never accepted as revisions.
The recursive exact-JSON snapshot node bound is derived from 4097 entries at
64 nodes each plus 1024 envelope nodes, so the public 4096-entry maximum is
accepted while a complete 4097-entry ledger remains outside the contract.

Every ledger has:

- `contract_state=SOURCE_REVALIDATION_REQUIRED`;
- `canonical_state=NOT_MINTED`;
- `persistence_observed=false`;
- `store_origin_authenticated=false`;
- `project_manifest_binding_verified=false`;
- `monotonic_anchor_present=false`;
- `rollback_detection_authority_created=false`;
- `consumer_revalidation_required=true`.

A parser proves only structural/hash consistency. It never recreates runtime
verification authority from JSON.

## 3. CAS and append evaluation

A CAS expectation binds ledger key, revision, latest entry, chain, and ledger
hash. It is structural and has `expectation_is_authority=false`.

Append evaluation accepts exact in-process typed ledger, CAS expectation, and
P1C-B read-back values. All are reserialized and strictly revalidated before
comparison. The proposed ledger must reconstruct the exact observed prior
ledger hash and bind the incoming read-back digest. A mapping or serialized
P1C-B projection is rejected.

Closed decisions:

| Decision | Meaning |
|---|---|
| `APPEND_CANDIDATE` | CAS matches and a new structurally valid candidate ledger is returned. |
| `DUPLICATE_CANDIDATE` | The same idempotency/source/Evidence/Human coordinates already exist; no new ledger is returned. |
| `ID_COLLISION_REJECTED` | A reused idempotency key, source record, or Evidence ID disagrees with existing coordinates. |
| `STALE_CAS_REJECTED` | Any expected revision/latest/chain/ledger coordinate differs. |

Duplicate classification is not canonical duplicate receipt lineage. It only
identifies an exact candidate already present in the supplied structural chain.

## 4. Transition invariants

Entries are strictly sequential, parent and prior-chain exact, and scoped to one
ledger key. The contract rejects gaps, forks, replayed entry hashes, duplicate
idempotency keys, duplicate source record IDs, duplicate Evidence IDs, and any
same-identity/different-coordinate collision inside a supplied ledger.

A newly appended candidate is revision `N+1`, parented to the current latest
entry, and chains from the current chain hash. It copies P1C-B coordinates but
sets runtime-readback authority false because a later side effect must rerun the
raw verifier under its own transaction lock.

## 5. Authority boundary

P1C-C does not establish or authorize:

- staging writer/store origin or Product Project root ownership;
- hostile ancestor race protection or post-return stability;
- filesystem/database/Project manifest write or directory durability;
- external monotonic anchor, rollback detection, canonical latest, or recovery;
- canonical store commit, receipt mint, or canonical admission;
- automatic learning/profile promotion, Timeline, Resolve, Provider, network,
  paid, native, Release, Deploy, or Production effects.

No serialized entry, ledger, CAS expectation, evaluation, self-hash, or proposed
ledger is authority. The later writer must rerun raw P1C-B verification, bind the
current Product Project manifest/revision under lock, perform atomic durable
promotion/recovery, read back the exact commit, and only then mint a receipt.

## 6. API

```text
MontageLearningCanonicalLedgerCandidate.empty(...)
MontageLearningCanonicalLedgerCandidate.from_dict(mapping)
MontageLearningCanonicalLedgerCasExpectation.for_ledger(ledger)
MontageLearningCanonicalLedgerCasExpectation.from_dict(mapping)
evaluate_montage_learning_canonical_append(ledger, expectation, readback)
MontageLearningCanonicalAppendEvaluation.to_dict()
```

There is no `open`, `load`, `save`, `write`, `replace`, `recover`, `get_latest`,
`mint`, `receipt`, Product Project, ProjectSave, network, or subprocess API.

## 7. Exact scope and acceptance

Exact six paths:

1. `docs/ai-team/tasks/TASK-058/task.md`;
2. this design;
3. `schemas/montage-learning-canonical-promotion-ledger-candidate.schema.json`;
4. byte-identical packaged Schema mirror;
5. `src/ai_video_production/montage_learning_canonical_promotion_ledger_contract.py`;
6. `tests/test_task058_montage_learning_canonical_promotion_ledger_contract.py`.

Acceptance requires Schema Draft 2020-12 and mirror parity; deterministic empty
and multi-entry vectors; full chain/parser checks; all four decisions; stale CAS
for every coordinate; idempotency/source/Evidence collision negatives; mapping
and fake read-back rejection; 192-character P1C-B identifier compatibility with
193-character rejection; exact built-in nested JSON containers; malicious
dict/string subclass rejection; bounded entry count; immutable/body-free
outputs; false authority/effect matrices; no prohibited I/O surface; focused
and direct regression; and independent Critic/Tester/Judge with C/H/M/L zero.
