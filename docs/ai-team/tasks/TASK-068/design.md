# TASK-068 design

## Boundary

`SecureAuthorityIO` is constructed with an absolute private root but performs no I/O until an operation is invoked. Every operation accepts only a bounded relative path. The public API is divided into effect-bearing v1 operations and fail-closed discovery surfaces:

- `read_json`
- `lock`
- `publish_json_noreplace`
- `publish_immutable_json(document, plan, lease)`
- `read_immutable_json(plan, expected_identity)`
- `inspect_immutable_graph(plans, expected_identities, specified_plan)`
- `replace_json_cas -> NoReturn` (`CAS_ATOMIC_UNAVAILABLE`)
- `cleanup_owned_file -> NoReturn` (`CLEANUP_ATOMIC_UNAVAILABLE`)
- `commit_directory_tree -> NoReturn` (`DIRECTORY_TREE_COMMIT_AUTHORITY_NOT_CREATED`)
- `advance_mutable_phase -> NoReturn` (`MUTABLE_PHASE_ADVANCE_UNAVAILABLE`)

Read results expose the decoded document, hash, byte count, and identity. Their representation intentionally omits the document. Publish receipts expose only hash, byte count, and identity. `SecureAuthorityIOError` exposes a stable code only.

## Binding and failure model

On POSIX, root and child directories are traversed with pinned directory descriptors and no-follow opens. Target opens are relative to the pinned parent descriptor. On Windows, directory and file handles are opened with `FILE_FLAG_OPEN_REPARSE_POINT`, made non-inheritable, and bound to `lstat` identity. Every platform rejects non-regular targets, reparse points, zero identities, and link counts other than one.

Directory mtime and size are allowed to change during an authorized namespace operation. Ancestor continuity therefore compares device, inode, file type, and reparse status. File continuity remains an exact identity comparison, including size and modification time.

All fault paths fail closed. Unknown temporary-file ownership is preserved rather than deleted. Errors never interpolate OS messages, paths, JSON bodies, or raw bytes.

## Durability and publication

Publication writes and re-reads canonical bytes through one live operation-owned handle before a namespace effect. POSIX requires `O_TMPFILE` and binds that unnamed inode to the final name with `linkat(AT_EMPTY_PATH)`, eliminating a substitutable temporary pathname. Windows uses `CREATE_NEW`, retains the live handle, and publishes it with handle-bound `FileRenameInfo` while pinned ancestors deny delete sharing. Both paths then perform directory durability and pinned readback.

`SUPERSEDED / IMMUTABLE_ONLY_V1`: same-path mutable CAS and published-artifact cleanup are not effect-bearing v1 responsibilities. Both discovery methods validate and consume a live writer capability, then fail before caller-document traversal, target read/open, hook seam, temporary creation, rename, exchange, rollback rename, or unlink. Their public errors have `completion_unknown=false` and `authority_created=false`; no consumer may convert either unavailable result to PASS or authority.

The Owner-approved `IMMUTABLE_ONLY_V1` Design Gate resolves the architecture boundary without weakening the uncooperative-writer threat model. A consumer supplies an exact generation coordinate already bound by a trusted Product plan and monotonic durable receipt: random operation ID, bounded revision, exact body digest, physical identity, and expected predecessor digest. TASK-068 may securely publish/read that exact immutable object and prove the specified predecessor-chain consistency, but it never creates or selects currentness authority.

The reserved `.immutable-authority/` namespace cannot be published through the raw `publish_json_noreplace` surface, including Windows case variants and any available physical short-name alias. Exact spelling is rejected lexically. For any other Windows first component, the raw effect parent is pinned and bound to the writer root before body traversal; the canonical reserved directory is then independently pinned under the same root, and their stable directory-object identities are compared while both handles deny rename/delete. Only after a proven non-match may body traversal, temporary creation, or namespace effect begin. `TrustedImmutablePlan` is audit data, not authority: the `SecureAuthorityIO` instance must be configured by the owning composition with an exact `authority_instance_id` and an opaque verifier that validates the complete plan fingerprint. A caller-created dataclass, wrong instance, missing verifier, invalid authorization, any semantic-field rebinding, malformed operation/revision/digest, or body-digest mismatch fails before namespace effect. The verifier—not TASK-068—owns signature/MAC policy and monotonic receipt issuance.

A transition is a separate immutable no-replace record binding predecessor digest/identity, new-generation digest/identity, action, operation, build, backend, and session. Revocation is an immutable tombstone/transition. Crash orphans are preserved and are neither adopted nor deleted; recovery requires a same-operation `ABORT` or `COMPENSATE` transition published no-replace, followed by fresh exact-coordinate inspection.

Bounded enumeration is an integrity check only. The trusted plan supplies the complete exact coordinate allow-list for one reserved namespace, and the owning composition supplies a second verifier over the aggregate plan fingerprints plus the specified coordinate. This consumer-owned verifier binds monotonic receipt state and rejects stale/replayed tombstone or disallowed action sequences without making TASK-068 a currentness state machine. Starting from the consumer-specified generation, inspection validates that allow-list, the reachable predecessor chain, pinned strict bytes/identity, and stable before/after namespace observations. It rejects unknown files, ambiguous JSON, reparse/hardlink, DACL drift, duplicate revision/operation/path/digest, cycle, missing predecessor, fork, unreachable generation, or cross-operation/cross-instance binding. Because directory enumeration is not a transactional currentness primitive, even a successful or repeated inspection says only that the observed supplied set was consistent; it never chooses a winner or derives consumer `DUPLICATE` by fixed-history last event, scan-highest, mtime, filename, lexicographic order, mutable pointer, content equality, or caller-selected unbound coordinate. Every receipt/status/error declares `authority_created=false`, `currentness_selected=false`, `CURRENT_HEAD_AUTHORITY_NOT_CREATED`, `DUPLICATE_CURRENTNESS_AUTHORITY_NOT_CREATED`, `DIRECTORY_TREE_COMMIT_AUTHORITY_NOT_CREATED`, and `MUTABLE_PHASE_ADVANCE_UNAVAILABLE`.

Windows handle-bound deletion remains a private primitive used only for exact operation-owned temporary/rollback cleanup inside authorized immutable publication and lock initialization. It is not reachable through `cleanup_owned_file` and does not authorize deletion of a published authority artifact. Physical GC belongs to a separate Task/Human Gate.

## Safety limits

The foundation does not create parent directories, commit directory trees/snapshots, advance mutable journal phases, select Production paths, grant provider/native authority, interpret Montage semantics, or perform Release/Deploy/Production Activation. It is an I/O primitive; caller Tasks remain responsible for authorization, schema, privacy projection, semantic validation, and effect gates. A consumer may compose exact immutable phase generations and terminal/tombstone records, but may not promote fixed journal updates, mutable pointers, directory rename, or derived current views to TASK-068 authority.

For TASK-067 mode routing, only `VERIFIED_READBACK/A2` may evaluate `read_json`/`read_immutable_json` as a strict pinned-read primitive candidate. `FRESH`, `PRECOMMIT_RESUME`, and `JOURNAL_RECOVERY` require write/state-transition authority that TASK-068 v1 deliberately does not create. Project manifest replacement, mutable phase journals, cleanup, and marker/anchor transitions remain unavailable; a TASK-068 audit receipt is never sufficient to claim any TASK-067 write mode complete.
