# TASK-068 — Secure Authority Artifact I/O Foundation

Status: `IMPLEMENTATION_COMPLETE / DEV-4 / IMMUTABLE_ONLY_V1 / DRAFT_PR_READY`

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
- `SUPERSEDED / IMMUTABLE_ONLY_V1`: same-path mutable identity-CAS is not an effect-bearing v1 responsibility. `replace_json_cas` is a `NoReturn` discovery surface that returns body-free `CAS_ATOMIC_UNAVAILABLE`, effect zero, and `authority_created=false` after consuming a valid writer capability.
- `SUPERSEDED / IMMUTABLE_ONLY_V1`: deletion of a published authority artifact is not an effect-bearing v1 responsibility. `cleanup_owned_file` is a `NoReturn` discovery surface that returns body-free `CLEANUP_ATOMIC_UNAVAILABLE`, effect zero, and `authority_created=false` after consuming a valid writer capability.
- Generation/transition publication requires an exact coordinate bound by a consumer-owned trusted Product plan and monotonic durable receipt: random operation ID, bounded revision, body digest, physical identity, expected predecessor digest, and an opaque verifier over the complete semantic fingerprint. Unbound or field-rebound caller coordinates are rejected.
- Graph inspection additionally requires a consumer-owned exact graph verifier over the complete allow-list fingerprint and specified coordinate. It proves consistency only for that specified chain and never selects a current/head/highest/latest generation. Fork, cycle, missing predecessor, unknown collision, orphan, stale/cross-operation/cross-instance coordinate, or replayed tombstone is STOP+preserve+effect zero.
- Revocation uses an immutable tombstone/transition. Published authority artifacts are never automatically deleted; physical lifecycle cleanup is a separate Task and Human Gate.
- Directory-tree/snapshot publication and mutable phase advance are not v1 authority. Their `NoReturn` discovery surfaces return `DIRECTORY_TREE_COMMIT_AUTHORITY_NOT_CREATED` and `MUTABLE_PHASE_ADVANCE_UNAVAILABLE` before path/body/effect.
- An immutable terminal record may be published/read only at its operation-specific exact coordinate. Re-publish collisions, fixed-history last-event inspection, or directory scan results never create a consumer `DUPLICATE`; statuses declare `DUPLICATE_CURRENTNESS_AUTHORITY_NOT_CREATED`.
- Public receipts and errors contain no path or document body.
- POSIX and Windows race/fault focused tests pass; unresolved Critical/High findings are zero.

## Dependencies and next task

TASK-069 may consume this foundation only after TASK-068 has a canonical completion receipt. TASK-067 may evaluate the strict pinned read primitive only for `VERIFIED_READBACK/A2`; TASK-068 creates no write-mode authority for `FRESH`, `PRECOMMIT_RESUME`, or `JOURNAL_RECOVERY`. Project-manifest mutable CAS, mutable journal phase, cleanup, marker/anchor transition, and directory-tree commit remain unavailable. No consumer may promote a TASK-068 receipt to completion for every TASK-067 mode.

Consumers must not infer authority from directory scans, highest-number selection, mtime, filename/lexicographic order, mutable pointers, content equality, fixed-history last event, directory-tree commit, mutable phase advance, or a TASK-068 receipt alone. All receipts/statuses declare `authority_created=false`, `currentness_selected=false`, `CURRENT_HEAD_AUTHORITY_NOT_CREATED`, `DUPLICATE_CURRENTNESS_AUTHORITY_NOT_CREATED`, `DIRECTORY_TREE_COMMIT_AUTHORITY_NOT_CREATED`, and `MUTABLE_PHASE_ADVANCE_UNAVAILABLE`. TASK-068 does not modify TASK-058/TASK-067/TASK-069 owner modules.
