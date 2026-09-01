# TASK-063 L3 Native QA Design Input for TASK-036 P0-E

Date: `2026-09-01`
Input contract: `TASK063-L3-NATIVE-QA-INPUT-V1`
State: `DESIGN_FIXTURE_READY / NATIVE_EXECUTION_START0`

## Authority boundary

TASK-063 design hash `F91C...` remains `C0/H4 / Judge FAIL`. It is neither a
completion receipt nor permission to install, provision, repair, update,
rollback, or clean a real installation. TASK-036 may consume only the future
trusted TASK-063 terminal handoff. This packet prepares native acceptance and
fault injection without changing TASK-063 source, installation state, shared
metadata, Release, Deploy, or Production.

The synthetic fixture is
`task063-l3-native-fault-fixture-v1.json`. It contains expected observations,
not executed Evidence. `authority_created=false` and every native/effect flag
must remain false until the separate Windows QA gate is opened.

## Native acceptance matrix

| ID | Precondition and seam | Required typed result | Required durable delta |
| --- | --- | --- | --- |
| I63-NQA-01 | absent operation lock; two provisioners cross the initial create barrier | one `ACCEPTED`, loser `CONFLICT_REQUIRES_FRESH_RESOLVE`; automatic retry zero | one lock identity, one descriptor generation, one receipt |
| I63-NQA-02 | existing safe lock and descriptor; two updaters bind the same predecessor | one `ACCEPTED`; other exact typed `STALE_PREDECESSOR`, or `DUPLICATE` only when it binds the same committed event | authoritative revision advances exactly once |
| I63-NQA-03 | operation-owned temp closes, then a foreign inode appears at publish target | `FOREIGN_TARGET_PRESERVED` | target overwrite/delete zero; receipt zero |
| I63-NQA-04 | descriptor publication becomes visible, then its directory durability port fails | `DESCRIPTOR_DURABILITY_UNKNOWN` | authoritative revision unknown; no terminal receipt; preserve and fresh pinned resolve |
| I63-NQA-05 | durable descriptor passes pinned readback, terminal receipt becomes visible, then receipt-directory durability fails | `RECEIPT_DURABILITY_UNKNOWN` | descriptor revision one; visible receipt non-authoritative; preserve/reconcile/no replay |
| I63-NQA-06 | descriptor target is swapped immediately after publish and before pinned readback | `POST_PUBLISH_IDENTITY_MISMATCH` | authoritative revision unknown; completion receipt zero; foreign target preserved |
| I63-NQA-07 | rollback current target becomes a foreign replacement | `ROLLBACK_FOREIGN_CURRENT_PRESERVED` | authoritative revision unknown; restore/delete zero; fresh pinned resolve |
| I63-NQA-08 | cleanup encounters a foreign replacement for an operation temp | `CLEANUP_FOREIGN_TEMP_PRESERVED` | unlink zero for foreign identity; predecessor remains authoritative |
| I63-NQA-09 | selected-root ancestor identity or DACL changes while operation lock is held | `SECURITY_CURRENTNESS_LOST` | descriptor/owner/readback/receipt mutation zero |

All scenarios also require unrelated installation instances and user data to
remain byte- and identity-unchanged. A path string, equal bytes, self-hash, or
public receipt cannot substitute for the bound opened identities.

## Required trusted Windows composition

The future QA runner must use an exact signed/tested native helper that:

1. opens the selected installation root and every relevant ancestor with
   nofollow/reparse rejection and records physical identity plus DACL/owner;
2. creates or opens the operation lock with `CREATE_NEW` initial semantics,
   regular-file/nlink-one validation and locking on that same handle;
3. binds descriptor, owner manifest, journal, predecessor and temp bytes to
   their opened handles and strict canonical JSON snapshots;
4. exposes deterministic test-only barriers around lock creation, temp close,
   publication, directory durability, post-publish readback and cleanup;
5. publishes only with noreplace or expected-target identity CAS;
6. makes directory durability failure observable and fail-closed rather than
   treating unsupported/failed flush as success;
7. performs post-publish readback through a pinned handle and proves the exact
   expected bytes, inode/file identity, revision, owner and selected instance;
8. removes only the operation-owned exact identity recorded in the journal.

Fault injection must be isolated to a QA build/composition and unavailable
from Production argv, config, receipt, environment, IPC, or public Python API.

## Evidence contract

The future private native receipt binds operation ID/action, TASK-063 instance,
package/build/helper hashes, Windows volume/filesystem, boot/session coordinate,
trusted clock, selected-root/ancestor/DACL identities, lock/descriptor/owner/
journal/temp/receipt opened identities, injected seam, typed result, before and
after revision, and unrelated-instance delta digest.

The public projection contains only opaque IDs, stable reason codes, hashes,
counts, booleans and `authority_created=false`. It contains no absolute path,
SID/account name, DACL body, OS error text, temp name, descriptor body, secret,
or private installation data.

## TASK-036 consumption

TASK-036 P0-E accepts TASK-063 only after the trusted terminal handoff proves
the selected package/EXE/build and current installed identity. A synthetic
fixture, design hash, directory existence, equal hash, or partial TASK-063
scenario PASS keeps `task063_terminal_handoff_consumed=false` and packaged
entry/first-run/native execution at START0.
