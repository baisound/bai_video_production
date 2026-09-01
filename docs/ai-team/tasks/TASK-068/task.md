# TASK-068 — Secure Authority Artifact I/O Foundation

Status: `CORRECTIVE_IMPLEMENTATION_COMPLETE / SUCCESSOR_REBIND_IN_PROGRESS / IMMUTABLE_ONLY_V1 / COMMIT_STOP`

## Responsibility

Provide one Product-local, production-authority-artifact I/O foundation so Montage Learning tasks do not independently reproduce security-sensitive path, JSON, lock, temporary-file, immutable publish, and durability behavior.

## Authority

Owner-approved source implementation and focused verification are authorized. Release, Deploy, Production Activation, native real-data effects, and edits to shared current-state, task-index, roadmap, CHANGELOG, `atomic.py`, or existing Montage owner modules are not authorized.

## Allowed files

- `src/ai_video_production/secure_authority_io.py`
- `tests/test_task068_secure_authority_io.py`
- `tests/test_task068_secure_authority_io_windows.py`
- `docs/ai-team/tasks/TASK-068/**`

## Acceptance

- Root and ancestors are pinned and rechecked; symlink/reparse traversal is rejected.
- Final files use no-follow/open-reparse semantics, handle-to-name identity binding, regular-file and `nlink == 1` checks, bounded reads, post-read identity checks, and non-inheritable handles.
- JSON parsing is strict UTF-8 with byte, depth, node, duplicate-key, non-finite-number, and malformed-input rejection.
- Existing and initial locks are securely opened/created and exclusively locked.
- Publish uses an owned exclusive same-directory temporary file, exact write readback, file durability, no-replace namespace publication, and directory/Windows write-through durability.
- A helper or asynchronous exception after native no-replace is classified from the still-live source handle and final name; only an exact foreign collision is confirmed no-effect, while owned or ambiguous publication is completion-unknown.
- `SUPERSEDED / IMMUTABLE_ONLY_V1`: same-path mutable identity-CAS is not an effect-bearing v1 responsibility. `replace_json_cas` is a `NoReturn` discovery surface that returns body-free `CAS_ATOMIC_UNAVAILABLE`, effect zero, and `authority_created=false` after consuming a valid writer capability.
- `SUPERSEDED / IMMUTABLE_ONLY_V1`: deletion of a published authority artifact is not an effect-bearing v1 responsibility. `cleanup_owned_file` is a `NoReturn` discovery surface that returns body-free `CLEANUP_ATOMIC_UNAVAILABLE`, effect zero, and `authority_created=false` after consuming a valid writer capability.
- Generation/transition publication requires an exact built-in private plan snapshot bound by a consumer-owned verifier. Its versioned fingerprint commits the flat two-component coordinate, operation/revision/action, body and predecessor digests, build/backend/session/instance bindings, and a digest of the opaque authorization. The verifier receives a separate canonical copy and cannot mutate the retained snapshot. The caller document is bounded and canonicalized once, then those exact bytes are published.
- Immutable readback requires a versioned trusted receipt whose fingerprint commits the plan fingerprint, exact body/count, full physical file identity, predecessor, and root/ancestor/target security commitment. A fresh caller-created or self-rehashed receipt is audit data only and cannot pass the consumer-owned receipt verifier.
- Trusted immutable filenames use the exact graph-scan filename grammar. Receipt byte counts and physical-identity integers are bounded before fingerprint encoding; custom `PathLike` and post-native helper failures are normalized outside active exception handlers to a body-free public code with no retained private cause/context.
- Graph inspection requires exact built-in plan and receipt snapshots plus a consumer-owned verifier over the aggregate trusted-receipt fingerprints and the specified trusted receipt. It proves consistency only for that specified chain and never selects a current/head/highest/latest generation. Fork, cycle, missing predecessor, unknown collision, orphan, stale/cross-operation/cross-instance coordinate, or replayed tombstone is STOP+preserve+effect zero.
- Revocation uses an immutable tombstone/transition. Published authority artifacts are never automatically deleted; physical lifecycle cleanup is a separate Task and Human Gate.
- Directory-tree/snapshot publication and mutable phase advance are not v1 authority. Their `NoReturn` discovery surfaces return `DIRECTORY_TREE_COMMIT_AUTHORITY_NOT_CREATED` and `MUTABLE_PHASE_ADVANCE_UNAVAILABLE` before path/body/effect.
- An immutable terminal record may be published/read only at its operation-specific exact coordinate. Re-publish collisions, fixed-history last-event inspection, or directory scan results never create a consumer `DUPLICATE`; statuses declare `DUPLICATE_CURRENTNESS_AUTHORITY_NOT_CREATED`.
- Writer capabilities are exact owner-issued objects and cannot be forged, subclassed, reset, or reused. Every accepted write attempt that raises burns the capability before the caller can try a different path/body/plan in the same context.
- Public receipts and errors contain no path or document body; receipt/identity objects remain non-authoritative audit data.
- Every exported operation and lock lifecycle reconstructs public failures at a detached boundary; parser documents, verifier exceptions, OS filenames, private cause, and private context are never retained on the returned error.
- POSIX focused tests pass on the no-force current-main successor; fresh Windows-native runtime remains `NOT_CONFIRMED` because this host lacks a pytest runner and no install/retry was attempted. Historical identical-content Tester, Critic, and Judge evidence is retained, while successor Critic/Judge rebind remains required. `COMMIT STOP` stays active until that final gate closes.

## Dependencies and next task

TASK-069 may consume this foundation only after TASK-068 has a canonical completion receipt. TASK-067 may evaluate the strict pinned read primitive only for `VERIFIED_READBACK/A2`; TASK-068 creates no write-mode authority for `FRESH`, `PRECOMMIT_RESUME`, or `JOURNAL_RECOVERY`. Project-manifest mutable CAS, mutable journal phase, cleanup, marker/anchor transition, and directory-tree commit remain unavailable. No consumer may promote a TASK-068 receipt to completion for every TASK-067 mode.

Consumers must not infer authority from directory scans, highest-number selection, mtime, filename/lexicographic order, mutable pointers, content equality, fixed-history last event, directory-tree commit, mutable phase advance, or a TASK-068 receipt alone. All receipts/statuses declare `authority_created=false`, `currentness_selected=false`, `CURRENT_HEAD_AUTHORITY_NOT_CREATED`, `DUPLICATE_CURRENTNESS_AUTHORITY_NOT_CREATED`, `DIRECTORY_TREE_COMMIT_AUTHORITY_NOT_CREATED`, and `MUTABLE_PHASE_ADVANCE_UNAVAILABLE`. TASK-068 does not modify TASK-058/TASK-067/TASK-069 owner modules.
