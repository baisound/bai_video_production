# TASK-058 P1B — Admission Staging Ledger Store Detailed Design

Date: 2026-08-26
Profile: DEV-4 FOUNDATION CRITICAL
Atomic Unit: P1B filesystem store / CAS / restart recovery
Base: eea0296dbbd49c5dfe43fe46df6d2955dbd711fe

## 1. Decision

P1B introduces one BAI VIDEO PRODUCTION-owned, body-free staging ledger for
caller-supplied exact-profile coordinate claims. It does not implement the
inbox importer, Human admission binding, canonical promotion, or receipt issuer.

The staging ledger deliberately creates no P0 source-origin, Human-binding,
monotonic-head, rollback-detection, canonical-store, or receipt authority.
P1C must revalidate the full P0 delivery, verify the exact Human binding, bind
a monotonic Project head, and atomically promote before a receipt may claim a
canonical_store_commit_sha256.

The generic bvp-montage-learning-adapter profile is rejected at this staging
boundary. A relabelled caller claim still remains non-authoritative because all
origin, canonical, rollback, promotion, and receipt flags are fixed false.

## 2. Responsibility boundary

### P1B owns

- exact on-disk staging shape and parser;
- one immutable staging-entry shape and domain-separated digest;
- contiguous in-file sequence and previous-entry hash chain;
- store/Owner scope immutability;
- optimistic expected_revision CAS;
- exact resend lookup without a second write;
- record-ID and canonical-evidence-ID collision rejection;
- atomic temp-write, file fsync, validation, replace, and read-back;
- explicit directory durability NOT_CONFIRMED result;
- restart read-back from the one staging path;
- fail-closed corruption and size handling;
- pre-existing/observed path refusal under a cooperative-local-writer model.

### P1B does not own

- inbox/outbox/quarantine path or file lifecycle;
- source file stability classification;
- Human confirmation or approval authority;
- canonical admission, monotonic head, or rollback-detection authority;
- use of a staging digest as canonical_store_commit_sha256;
- public receipt origin or canonical commit verification;
- public BvpMontageLearningAdmissionReceipt/v2 minting;
- duplicate receipt lineage publication;
- Timeline, TASK-029 Owner Profile, Knowledge Pack, Resolve, or runtime effects;
- connector installation, application launch, network, database, or provider I/O.

## 3. Staging path

The store is constructed with an exact Product Project root and uses:

state/montage-learning-admission-staging-ledger.json

The root must already be a regular non-reparse directory. Existing state and
target paths must not be symlinks, junctions, or another reparse point. The
update lock is created at the verified Project root, not inside state.
Project-root device/inode identity and root/state/target reparse status are
rechecked before lock, inside lock, at every exposed AtomicJsonWriter failure
phase, and on read-back.

The exact path security model is COOPERATIVE_LOCAL_WRITER_ONLY. These checks
reject pre-existing and observed path changes, but hostile concurrent path-race
protection is NOT_CONFIRMED: AtomicJsonWriter can resolve a path again after a
check, including before temp creation or replace. external_effect_authorized=false
is an authorization boundary, not proof against malicious filesystem
redirection. P1C must use a handle-bound writer for canonical promotion.


implementation creates only the missing state directory and the exact ledger
file. Callers cannot supply a relative store path.

The ledger contains only body-free coordinates. DPAPI is not required for P1B
because no evidence body, actor/account identity, path, transcript, media, key,
credential, or secret is persisted. If a later Unit persists sensitive body
data, it requires a separate privacy/storage design rather than widening P1B.

## 4. Ledger document

Identity:

- schema_version = 1.0.0
- record_type = MONTAGE_LEARNING_ADMISSION_STAGING_LEDGER
- task_owner = TASK-058
- store_id
- owner_scope_hash

State:

- revision, exactly equal to len(entries);
- entries, ordered and contiguous within the current staging snapshot;
- ledger_sha256, domain-separated digest of every other ledger field.

Path-security boundary:

- path_security_model = COOPERATIVE_LOCAL_WRITER_ONLY
- hostile_path_race_protection_verified = false
- handle_bound_canonical_promotion_required = true

Permanent false authority boundaries:

- generic_observation_admission_authorized = false
- automatic_learning_promotion_authorized = false
- receipt_mint_authorized = false
- canonical_store_write_authorized = false
- monotonic_head_anchored = false
- rollback_detection_authority_created = false
- timeline_mutation_authorized = false
- resolve_write_authorized = false
- external_effect_authorized = false

## 5. Entry document

Each entry contains sequence, canonical_evidence_id, source_contract_profile,
source_record_id, source_sha256, owner_scope_hash, idempotency_key_sha256,
canonical_evidence_sha256, human_binding_sha256, committed_at,
previous_entry_sha256, and entry_sha256.

Entry boundary flags are staging_store_written=true while
exact_evidence_coordinates_structurally_verified=false,
human_binding_origin_verified_by_store=false, canonical_store_written=false,
canonical_admission_authority_created=false,
rollback_detection_authority_created=false, receipt_minted=false,
automatic_learning_promotion_authorized=false,
timeline_mutation_authorized=false, and external_effect_authorized=false.

entry_sha256 uses the domain
TASK058_MONTAGE_LEARNING_ADMISSION_ENTRY_V1 NUL plus canonical JSON without the
entry_sha256 field. ledger_sha256 uses
TASK058_MONTAGE_LEARNING_ADMISSION_LEDGER_V1 NUL plus canonical JSON without the
ledger_sha256 field.

The entry digest identifies only the staging snapshot entry. It is explicitly
forbidden as canonical_store_commit_sha256. P1C must create a new commit only
after source/Human revalidation and monotonic Project anchoring.

## 6. Append algorithm

Before lock creation, P1B validates Project-root identity and reparse state.
Within the root-level exclusive update lock:

1. revalidate root/state/target identity and path safety;
2. load and fully verify the staging ledger, or construct revision zero;
3. require exact store_id and owner_scope_hash;
4. recompute the P1A idempotency digest from claimed source coordinates;
5. reject the Generic profile before any write;
6. resolve an existing key: exact coordinates return DUPLICATE_STAGED with no
   write; differing coordinates fail closed;
7. reject record, source digest, evidence ID, or evidence digest replay;
8. require current.revision == expected_revision;
9. append an in-snapshot sequence and prior-entry hash;
10. preflight the exact canonical JSON plus newline against the size limit;
11. atomically write with path identity checks at every exposed phase;
12. reload the staging path and require exact ledger/entry digest read-back;
13. return STAGED and directory durability NOT_CONFIRMED.

Duplicate resolution precedes CAS so a stopped caller can recover the same
staging entry without a second staging write. This does not recover or prove a
canonical admission.

## 7. Restart and failure model

The store uses one staging file and no two-file transaction journal.

- stop before replace: the old staging snapshot remains readable;
- stop after replace: the new staging snapshot is read back;
- directory-entry durability is explicitly NOT_CONFIRMED;
- leftover temp files are never scanned, parsed, promoted, or deleted by load;
- corrupt staging fails closed and never falls back to a temp file;
- missing staging becomes revision zero only through load_or_empty;
- deletion or replacement with an older valid snapshot is not detectable by
  P1B and therefore creates no monotonic or rollback-detection authority;
- oversize/pre-replace/path-identity failure preserves the old snapshot;
- an exact retry recovers only the same staging entry.

P1C must bind a separate monotonic Project anchor before canonical promotion.
P1B exposes no delete, repair-from-temp, overwrite, or canonical promotion API.

## 8. Collision and replay rules

- same idempotency key and exact coordinates: DUPLICATE_STAGED;
- same idempotency key with differing coordinates: integrity failure;
- same source_record_id with different source/evidence: ID_COLLISION;
- same source_sha256 under another record: replay rejection;
- same canonical_evidence_id with different coordinates: ID_COLLISION;
- same canonical evidence digest under a new ID: replay rejection;
- store ID or Owner scope mismatch: authorization failure;
- noncontiguous sequence/chain or checksum mismatch: integrity failure;
- unknown fields or versions: integrity failure.

No duplicate path increments revision or rewrites the file.

## 9. Public result and authority

MontageLearningAdmissionStoreResult returns STAGED or DUPLICATE_STAGED, a
verified typed staging entry/snapshot, and AtomicWriteResult only for STAGED.
Its durability_state is DIRECTORY_DURABILITY_NOT_CONFIRMED or NO_WRITE.
Its path_security_state is always
HOSTILE_PATH_RACE_PROTECTION_NOT_CONFIRMED.

The result is internal staging evidence. It is not a public admission receipt,
does not verify source/Human/receipt origin, cannot be used as a canonical store
commit, and creates no Timeline/runtime authority.

## 10. Error taxonomy

- ERR_TASK058_MONTAGE_STORE_PATH_UNSAFE
- ERR_TASK058_MONTAGE_STORE_INTEGRITY
- ERR_TASK058_MONTAGE_STORE_SCOPE
- ERR_TASK058_MONTAGE_STORE_CONFLICT
- ERR_TASK058_MONTAGE_STORE_GENERIC_FORBIDDEN
- ERR_TASK058_MONTAGE_STORE_READBACK
- ERR_TASK058_MONTAGE_STORE_SIZE

All errors are ProductError and fail closed.

## 11. Schema

The Draft 2020-12 schema is exact and closed. The public file and packaged
resource mirror are byte-identical. Runtime parsing remains authoritative for
hash-chain, uniqueness, ordering, cross-field, and digest semantics that JSON
Schema cannot express alone.

## 12. Verification matrix

Required focused tests cover schema/mirror parity, empty/first/two-entry writes,
restart read-back, exact resend without byte change, record/evidence collision,
same-source replay, idempotency mismatch, Generic rejection, scope/CAS mismatch,
structural/hash corruption, symlink/reparse and pre-lock refusal, root identity
change, write-size preflight preserving old bytes, UTF-8/JSON failure, atomic
failure phases, abandoned temp isolation, corrupt-staging no fallback, explicit
canonical/monotonic/rollback false flags, cooperative-only path model,
hostile path-race NOT_CONFIRMED, mandatory handle-bound P1C promotion,
directory durability NOT_CONFIRMED, and prohibited public capabilities.

Related regression covers P0 and P1A. Independent Tester and Critic must report
zero unresolved Critical/High findings before Judge GO.

## 13. Allowed files

1. docs/ai-team/tasks/TASK-058/task.md
2. this design
3. schemas/montage-learning-admission-ledger.schema.json
4. its packaged byte-identical schema mirror
5. src/ai_video_production/montage_learning_admission_store.py
6. tests/test_task058_montage_learning_admission_store.py

## 14. Stop conditions

Stop and recover if Generic observations can enter the ledger, duplicates can
rewrite state, staging identity cannot bind exact idempotency/source/Owner
scope, corrupt staging can fall back to a temp, oversize can replace old state,
P1B claims canonical/monotonic/rollback/durability or hostile-path-race
authority, handle-bound P1C promotion ceases to be mandatory, P1C authority
leaks into P1B, or target paths overlap another lane.
