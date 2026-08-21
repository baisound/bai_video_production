# TASK-041 Audio Completion Native Immutable Ledger Store R1B Evidence

Date: 2026-08-21
Base: `b60c3ce9e1030a2235b046d28c3bbddfdd48cabe`
Branch: `codex/task-041-audio-completion-ledger-store-r1b-r0`
Development depth: `DEV-4 FOUNDATION CRITICAL`

## Result

R1B implements a cooperative Windows point-in-time namespace store for the
R0/R1A Audio Completion candidate ledger. It consumes R0/R1A contracts without
changing them. It does not mint canonical PASS/current/latest state and does
not authenticate upstream owners or storage origin.

The production backend accepts no caller path. It opens only the fixed volume
root by pathname, then uses `NtCreateFile` with a held parent handle for every
child open/create. Enumeration uses `NtQueryDirectoryFile` with 128-bit
`FileIdExtdDirectoryInformation`; there is no `FindFirstFile`, `pathlib.Path`,
`os.open`, glob, or absolute child-open fallback.

## Exact scope

Only these seven files are in scope:

1. `src/ai_video_production/audio_completion_ledger_store.py`
2. `src/ai_video_production/audio_completion_ledger_windows_port.py`
3. `schemas/audio-completion-ledger-store-receipt.schema.json`
4. `src/ai_video_production/schema_resources/audio-completion-ledger-store-receipt.schema.json`
5. `tests/test_task041_audio_completion_ledger_store.py`
6. `tests/test_task041_audio_completion_ledger_windows_port.py`
7. `docs/ai-team/tasks/TASK-041/audio-completion-native-immutable-ledger-r1b-evidence-2026-08-21.md`

R0, R1A, TASK-036, CHANGELOG and current-state files were not modified.

## Frozen contract

- The ledger root and exact zero-byte `.global.lock` anchor must already exist.
- The volume must be fixed-local NTFS; production never creates directories,
  changes ACLs, elevates, or repairs the root.
- Directory, lock, pending and final handles are non-inheritable, non-reparse,
  same-volume and held without delete sharing.
- Owner/DACL verification is handle-based, non-null and fail-closed. Volume and
  system ancestors are identity-only trust anchors. The canonical root requires
  a protected private DACL; lock/final/pending children may use safe inherited
  owner/System/Administrators ACEs. Untrusted write/delete/DAC/owner ACEs,
  callback/unknown ACEs and elevated execution are rejected. R1B never mutates
  ACLs.
- The global zero-byte anchor is locked with one nonblocking exclusive
  `LockFileEx` range `(offset=0, length=0xffffffffffffffff)`. `LOCK_BUSY` is not
  retried. All observe/append/inspect/resume APIs use the same helper and lock.
- After every acquisition, the root/anchor are reverified and the complete
  bounded namespace, chain and pending set are reconciled. No abandoned-owner
  observation is claimed.
- Final names are `<ledger-key-digest>-<revision:08d>.json`; revisions 1..256
  and a 257 sentinel are opened only relative to the held root.
- Stored bytes are canonical JSON plus one LF. R1A canonical entry bytes are
  limited to 4 MiB, stored bytes to 4 MiB + 64 KiB, chain disk bytes to 16 MiB,
  pending count to 8 and pending bytes to 16 MiB. Bounds are rechecked under
  lock immediately before `CREATE_NEW`.
- `prepare_append` returns a sealed, non-pickleable 32-byte OS-random recovery
  token before the first possible mutation. Raw tokens never enter JSON,
  receipt, schema, public output, repr or logs; only a domain-separated digest
  is persisted and compared with `hmac.compare_digest`. The public
  `prepare_append` function and a resolve-only helper share a closure-private
  weak issuance registry; no build/issue/register callable is exposed as a
  module global. The registry retains canonical immutable snapshots of the
  complete key, candidate, CAS and token. Append reparses and constant-time
  compares every live slot with that snapshot, then uses only reconstructed
  snapshot values; slot mutation, direct/non-CSPRNG forging, copying and
  pickling are rejected. This is same-process misuse resistance, not a claim
  against arbitrary malicious code already executing inside the process.
- Pending creation is `CREATE_NEW | WRITE_THROUGH`, followed by exact write,
  file-only `FlushFileBuffers`, same-handle readback and FileId observation.
- Rename uses only `SetFileInformationByHandle` information class 22, flags 0,
  a held root handle and an ASCII root-relative target. There is no replace or
  fallback path.
- Recovery binds token hash, root identity, pending-creation FileId observation,
  rename-continuity FileId, exact payload, ledger key/revision and the full R1A
  CAS expectation digest. Pending and final namespace reconciliation must bind
  the same FileId; a byte-identical replacement final with a different FileId
  is rejected. Resume revalidates each binding under the live global lock.
- Immediately before rename, R1B revalidates the held root/lock, the original
  pending handle, payload and FileId, plus the old full chain and CAS. After a
  returned-true rename it verifies the renamed original handle, closes it,
  reopens the final by the canonical relative name, checks exact FileId/bytes,
  and derives the new full chain from a fresh bounded namespace scan.
- Pending-only, final-only, both, neither and different-final are distinct.
  Exact final returns `ALREADY_COMMITTED_RECONCILED` without another write.
  Exact pre-existing pending bytes reconstruct the sealed recovery receipt
  without another write. Partial, corrupt and individually oversized pending
  wrappers remain bounded read-only observations and block mutation. No pending
  file is automatically deleted or promoted.
- `namespace_state`, `content_state` and `pending_state` describe the recovery
  target. `pending_count`, `pending_disk_bytes` and `global_pending_state`
  describe the bounded root-wide pending aggregate. A successful target append
  therefore remains `FINAL_ONLY` even when another valid pending file remains;
  that separate global pending fact is retained.
- Rename, namespace, content, file-flush/reopen observation, resource release,
  pending, chain and commit states are orthogonal. A fault after rename TRUE
  retains known commit truth. A syscall-completion-unknown result is reconciled
  under lock and remains unknown only if the resulting namespace is ambiguous.
- Directory flush and power-loss durability are not claimed. WORM, owner-death
  detection, canonical admission, PASS/current/latest and R2 readiness are not
  claimed. Release failures do not rewrite commit truth.
- Store receipts always state `receipt_is_authority=false`,
  `consumer_revalidation_required=true` and
  `post_return_state_guaranteed=false`. Native/cleanup faults retain observed
  phase facts, while unlock/close failures are reported independently from
  namespace commit truth and unreleased-handle count.
- Store and public receipts use `entry_count` as the sole authoritative
  point-in-time chain-tip/count scalar. The redundant `final_count` and target
  `entry_revision` fields are absent and rejected as unknown. The recovery
  receipt alone carries the incoming `entry_revision`; it does not duplicate
  the observed prefix count. This makes the closed shape enforceable without
  cross-field revision/count arithmetic or hundreds of schema branches.
- Read and write attempts are distinct from observed effects. The receipt also
  preserves whether the lock was ever acquired, lock release truth, retained
  native handle count and retained LocalAlloc-family allocation count. A
  rename-returned-true fault keeps `KNOWN_COMMITTED` while clearing unverified
  namespace counts/digests to `NOT_OBSERVED`; it does not escape the API.
- Final enumeration and direct-probe handles are closed immediately after their
  verified read. The production native tracker, runtime receipt parsers and
  private/public schemas share an exact retained-handle cap of 32; the bounded
  protocol's worst normal namespace scan retains only the six root/lock handles
  plus at most eight pending handles, while a failed immediate close remains
  tracked and is surfaced without escaping the API.
- Runtime, public projection and schema share closed success-decision reason,
  operation, rename, commit, target-state, global-pending, chain, phase and
  release constraints. Self-resigned impossible tuples are rejected. A single
  mutation parity matrix starts from runtime-generated examples of all eight
  decisions and varies every closed enum, boolean, nullable target coordinate
  and representative count. Private runtime/schema and public runtime/schema
  acceptance remain identical with zero mismatches.
- Every success decision requires confirmed release, confirmed lock release and
  zero retained handles/native allocations. Any cleanup failure downgrades a
  generated success to `INCOMPLETE`; self-resigned success with incomplete or
  unknown release is rejected by private runtime, public runtime and schema.
- `OBSERVED` separates the target from the global pending aggregate. An empty
  ledger reports target `NEITHER`/`NOT_OBSERVED` with null target coordinates;
  a nonempty ledger reports target `FINAL_ONLY`/`FINAL_VERIFIED`, final reopen
  observation and the latest private target coordinates. Pending or corrupt
  files affect only `pending_count`, `pending_disk_bytes` and
  `global_pending_state`. `NOT_COMMITTED` always has target `NEITHER` and null
  private target coordinates. Empty chain/pending aggregates require zero disk
  bytes, and a nonempty chain requires positive disk bytes. A target or global
  pending observation may be `RECOVERABLE`/verified only with positive pending
  count and positive observed bytes. A positive count with zero bytes is
  retained only as a separate corrupt, nonverified observation.

## Finding closure

- Tester H1: exact global anchor, stable machine-wide coordinate, immediate
  exclusive range lock and full post-lock reconciliation are implemented and
  covered by lock-busy/two-port tests.
- Tester M3: digest/revision flat names, 1..256 direct probes and revision 257
  sentinel are implemented and tested.
- Critic M2: all child opens/creates and enumeration are handle-relative;
  canonical ASCII names are re-opened and their FileIds reverified.
- Critic M4: lock anchor regular/zero-byte/hardlink/same-volume/final-path/
  FileId/owner/DACL checks and release-state separation are implemented.
- Earlier H/M findings for no-replace atomicity, truthful rename/commit states,
  sealed recovery, CAS live validation, bounds and strict schema/privacy are
  bound to the two focused test files. Windows ABI widths, NTSTATUS handling,
  malformed enumeration, ACL policy and cleanup faults are covered through
  pure/fake seams only; no real native execution is claimed.
- Cycle-1 DACL findings are closed by role-separated ancestor/root/child
  validation and safe inherited child ACE handling without ACL mutation.
- Cycle-1 share/race findings are closed by retaining the pending handle,
  same-handle pre/post-rename validation, close-before-reopen, and old/new full
  chain scans shared by append and resume.
- Cycle-1 recovery/receipt findings are closed by prefix root/CAS validation,
  exact-pending receipt reconstruction, bounded corrupt-pending observation,
  replay reconciliation, fixed non-authority flags, truthful create/resume
  write phases, and explicit lock/handle release facts.
- Cycle-2 state findings are closed by non-escaping resume post-rename faults,
  target/global-pending separation, final-only versus both/conflict decisions,
  exact recovery rebinding, attempted/observed phases, lock-was-acquired truth,
  and shared runtime/public/schema negative tests.
- Cycle-2 native-resource findings are closed at the code/fake-test boundary by
  fixed-width Windows structures/NTSTATUS, internal handle/allocation trackers,
  bounded public counts, partial descriptor cleanup, malformed directory record
  rejection, and role-separated pure DACL policy tests.
- Recovery-session findings are closed by the private immutable prepared
  snapshot registry, pending-to-final FileId continuity receipt, immediate
  final/probe handle close, a shared cap of 32, all eight generated decision
  roundtrips, and private/public/schema rejection of impossible
  operation/decision/reason/rename/commit/count/coordinate tuples.
- Parity-hardening findings are closed by making the public prepare closure the
  only issuance path, retaining only a resolve helper at module scope, and
  exercising the canonical decision predicate against the private/public
  Draft 2020-12 projections with zero single-mutation parity mismatches.
- Semantic-closure findings are covered independently from parity by an
  expected-reject adversarial corpus for release state, empty/nonempty observed
  target state, target coordinates and count/byte invariants.
- Structural-semantic findings are closed by removing receipt-level duplicate
  revision/count representations. Tests exhaust all 257 x 257 equality and
  inequality pairs for legacy `final_count` and target `entry_revision`
  injection, verify all 1..256 recovery revisions without a duplicate count,
  and exercise private/public/schema pending count/byte/state combinations.
  A runtime-generated zero-byte pending observation is accepted only as
  `CORRUPT`, never as verified or recoverable.

## Verification

Focused command:

```text
wsl.exe -d Ubuntu --cd /mnt/c/home/baisound/worktrees/bai-video-production/task-041-audio-completion-ledger-store-r1b-r0 python3 -B -m pytest -p no:cacheprovider tests/test_task041_audio_completion_ledger_store.py tests/test_task041_audio_completion_ledger_windows_port.py -q
```

Fresh-main result: `79 passed in 7.83s`

Related command and exact file list:

```text
wsl.exe -d Ubuntu --cd /mnt/c/home/baisound/worktrees/bai-video-production/task-041-audio-completion-ledger-store-r1b-r0 python3 -B -m pytest -p no:cacheprovider tests/test_task041_audio_completion_receipt.py tests/test_task041_audio_completion_ledger_contract.py tests/test_task041_audio_completion_ledger_store.py tests/test_task041_audio_completion_ledger_windows_port.py -q
```

Fresh-main result: `133 passed in 8.54s`

Static compile/JSON parse used the bundled Python with `compile()` and
`json.loads()` so no bytecode/cache was written. Result: `STATIC_OK`.

The schema and resource mirror are byte-identical and Draft 2020-12 schema
validation is exercised by the focused suite.

## SHA-256 checkpoint

```text
fecb5b5fad12a08fafe8a5822fadc8845a943395323b8060b6c2860a5e5f1466  src/ai_video_production/audio_completion_ledger_store.py
966d619ed0d73868d40065c1d7ec44e3a31e5a5c6cd4dcf9467821d6dbf47144  src/ai_video_production/audio_completion_ledger_windows_port.py
c4ef1fb20129d184109134bb0731314ddbc6b37a3f3d9448892785ef6a2a5ff0  schemas/audio-completion-ledger-store-receipt.schema.json
c4ef1fb20129d184109134bb0731314ddbc6b37a3f3d9448892785ef6a2a5ff0  src/ai_video_production/schema_resources/audio-completion-ledger-store-receipt.schema.json
42fd445211662a3aa135a04dbad9cbfbde6cf7443b2415618a07b730a4d3bcb8  tests/test_task041_audio_completion_ledger_store.py
c00a2e257cd6fdbd11f0bb3ebe1e453d237c001ccc72e5425d83ee3c5f6bf888  tests/test_task041_audio_completion_ledger_windows_port.py
```

## Human/native gate

No real Windows ledger root, native filesystem operation, application launch,
temporary native directory, network, install, E: drive, model, audio or effect
operation was executed. Native Windows temporary-directory validation remains
`NOT_CONFIRMED` and requires a separate current Owner gate. Production root
provisioning and ACL changes remain outside R1B.

R2 remains responsible for owner API/source-origin revalidation, canonical
PASS/current/latest handling and TASK-036 consumption.
