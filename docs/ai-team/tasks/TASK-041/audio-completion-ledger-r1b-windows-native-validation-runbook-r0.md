# TASK-041 R1B Windows Native Validation Runbook R0

Status: `INSTRUCTIONS_ONLY / NV1 NOT_EXECUTED`
Date: `2026-08-22`
Dependency: `GitHub PR 270 / commit e337759`

This runbook defines the bounded Windows native validation gate for the
TASK-041 R1B Audio Completion immutable ledger store. NV0-A creates only this
document. It does not authorize or perform native calls, create a temporary
directory, launch a harness, install software, use the network, or access
audio, models, private media, or the E: drive.

## 1. Dependency and authority boundary

- NV1 depends on GitHub PR `270` and commit
  `e337759`. Before any native effect, the exact implementation under test must
  include that commit and the operator must record the full checked-out HEAD.
  A branch name, conversation claim, or PR number alone is insufficient.
- Verify the dependency with a read-only ancestry check equivalent to
  `git merge-base --is-ancestor e337759 HEAD`. Any nonzero result is `NO-GO`.
- The Owner sleep Gate is time-bounded native-execution authority. A new NV1
  validation call may start only while the current canonical Gate explicitly
  says `OPEN`. Post-expiry cleanup is limited to the exact reservation in
  section 6. Do not infer
  that the Owner is asleep, reuse an expired window, or treat this runbook as
  authority. If the Owner is awake, the window has expired, or the current
  record is ambiguous, result is `NOT_CONFIRMED` and no native effect starts.
- A pre-execution secretary delivery receipt is a hard Gate. Before any native
  or temporary-filesystem mutation, the committed runbook must be delivered and
  read back with the exact fields in section 11.1. A sent message without a
  delivery/readback observation is insufficient. The later NV1 outcome memo is
  a separate record and cannot satisfy this pre-execution Gate retroactively.
- R1B receipts remain diagnostic and non-authoritative. Native validation must
  not mint canonical PASS/current/latest state, storage-origin authentication,
  upstream-owner authentication, durability, WORM, or R2 readiness.
- NV1 is a validation activity only. Release, deploy, Production Activation,
  production data migration, ACL repair, and production ledger writes remain
  outside this gate.

## 2. Absolute production-path deny

Before any filesystem access, textually reject candidate coordinates that are
UNC, device/NT namespace, volume-GUID syntax, subst, E:, repository/project/
worktree paths, or configured private voice/media/model/AI coordinates. This is
a string-only deny: do not stat, open, resolve, enumerate, or otherwise probe E:
or another forbidden coordinate. `QueryDosDeviceW` may inspect the candidate
drive mapping as namespace metadata before access; a subst/device/forbidden-root
mapping is rejected without opening its target.

After textual rejection, open only the selected temporary parent read-only and
fail when its handle-resolved location would place the proposed validation root
at any of the following:

1. the R1B production root constant;
2. the Windows ProgramData known folder itself or any descendant;
3. an alias, junction, symlink, mount point, short-name alias, case variant, or
   final-handle path resolving to either location.

Use Windows Known Folder APIs, volume GUIDs, volume identity, FileId, mount
coordinates, and final paths obtained from handles for this comparison. Compare
all known aliases of the forbidden roots without opening those forbidden roots.
Do not rely on a textual `%ProgramData%` expansion. After creating the owned
outer container and ledger root, repeat the comparison using their handles
before creating `.global.lock` or invoking the store. This deny is absolute
even when the Owner sleep Gate is open.

## 3. NV1 prerequisites

All prerequisites must be recorded before the first filesystem mutation:

1. PR 270 dependency and exact commit ancestry are confirmed.
2. The committed runbook commit, blob id and SHA-256 plus the task/thread/message
   delivery identifiers, recipient, `sent_at` UTC, delivery status and readback
   status have been received back from the secretary. No mutation precedes this
   receipt.
3. The current Owner sleep Gate identifier, authority-record revision/digest,
   opening time, expiry time, scope, operator, and whether it reserves exact
   cleanup of this run's self-created artifacts after expiry are present and
   the Gate is still `OPEN`.
4. A reviewed NV1 harness is pinned by repository-relative path and SHA-256.
   The harness has no install, network, audio, model, private-media, E: drive,
   release, deploy, or production-root code path.
5. The harness supports a private process-local root binding before the first
   store call. It does not add caller path authority to the public product API.
6. `GetTempPath2W` returns the current-user temporary parent. That parent already
   exists, is ASCII-safe, is contained by the current-user LocalAppData known
   folder, is fixed-local NTFS, and every traversed component is non-reparse.
   There is no fallback and the harness never creates or repairs the parent.
7. The machine is Windows, the selected volume is fixed-local NTFS, and the
   process token is non-elevated. Remote, removable, ReFS/FAT/exFAT, WSL,
   container-mapped, subst, network, or unknown volumes are `NO-GO`.
8. The harness can create a cryptographically random ASCII-only outer-container
   name and ledger-root name,
   verify every traversed component by handle, apply and read back the exact
   DACL below, create the exact lock anchor, and perform handle-relative strict
   cleanup.
9. Private and public receipt schemas from the exact implementation checkout
   are loaded locally and their SHA-256 values are recorded. No schema or code
   is downloaded during NV1.
10. The test-only fault seams for pending retention, rename completion unknown,
    returned-true post-rename observation failure, and release failure are
    reviewed and cannot affect production configuration.
11. Pure/fake cleanup tests already prove fail-closed preservation for a foreign
    child, reparse entry, identity mismatch and ADS mismatch. Their exact test
    command, source/test hashes and PASS result are bound without creating any
    native NV1 adversarial fixture.
12. The later outcome-memo destination and the fields in section 11.2 are
    prepared separately from the pre-execution delivery receipt.

If any prerequisite is absent, stop before mutation. Do not install, download,
repair, elevate, or retry in order to make the prerequisite pass.

## 4. Temporary root construction

### 4.1 Selection and secrecy

- Obtain the current-user temporary parent only from `GetTempPath2W`. It must be
  an existing ASCII-safe descendant of the current-user LocalAppData known
  folder. Reject a missing, non-ASCII, non-contained, reparse, redirected,
  remote, removable, subst, or non-NTFS result. Do not create a parent and do
  not fall back to another directory.
- Generate one 32-byte CSPRNG run nonce in controller memory. Derive separate
  ASCII leaf labels for an owned outer container and ledger root; each label
  must match `bai-task041-nv1-[a-z0-9]{32}` with a distinct domain. The layout
  is exactly `temporary-parent / owned-outer / {ownership-marker, ledger-root}`.
  The marker is beside, never inside, the ledger root. The temporary parent is
  never owned by NV1 and must never be a cleanup target.
- The outer container and ledger root must be on the same fixed-local NTFS
  volume and must not resolve through a reparse point. Open and hold the
  parent/outer/root handles and verify final path, volume GUID and identity,
  FileId, link count, attributes, filesystem type, and forbidden-root aliases
  before ledger execution.
- Run non-elevated. An elevated or indeterminate token is `NO-GO`.
- Never place the raw validation root or raw recovery token in command-line
  arguments, environment variables, console output, test names, exceptions,
  logs, receipts, evidence, screenshots, clipboard, or secretary delivery.
  Persist only per-run salted, domain-separated SHA-256 bindings.
- Salt machine, volume, outer-container and ledger-root identity bindings with
  the CSPRNG run nonce using different fixed domains. Persist neither the raw
  identifiers nor the raw nonce. The resulting digests are correlation-limited
  to this run and do not establish reusable machine or storage authority.

### 4.2 Exact root DACL

Construct the owner and protected exact DACL before any owned-directory
creation. Create both outer container and ledger root with exact parent-relative
`NtCreateFile`; there is no create-then-fix ACL window. Freeze the directory
create ABI as follows:

- `OBJECT_ATTRIBUTES.RootDirectory`: held verified parent handle;
- `OBJECT_ATTRIBUTES.ObjectName`: one exact relative ASCII component;
- `OBJECT_ATTRIBUTES.Attributes`: `OBJ_CASE_INSENSITIVE` only, explicitly
  omitting `OBJ_INHERIT`;
- `OBJECT_ATTRIBUTES.SecurityDescriptor`: pointer to the exact self-relative
  owner/protected-DACL security descriptor;
- desired access: `FILE_LIST_DIRECTORY | FILE_ADD_FILE |
  FILE_ADD_SUBDIRECTORY | FILE_TRAVERSE | FILE_READ_ATTRIBUTES | READ_CONTROL |
  SYNCHRONIZE`;
- share access: `FILE_SHARE_READ | FILE_SHARE_WRITE`, without delete sharing;
- create disposition: `FILE_CREATE`;
- create options: `FILE_DIRECTORY_FILE | FILE_OPEN_REPARSE_POINT |
  FILE_SYNCHRONOUS_IO_NONALERT`;
- file attributes: `FILE_ATTRIBUTE_DIRECTORY`; allocation size/EAs: absent.

Require success status and `IO_STATUS_BLOCK.Information=FILE_CREATED`. Call
`GetHandleInformation` on the returned handle and require
`HANDLE_FLAG_INHERIT=0`. Read owner, DACL, final path, volume, FileId, link count,
attributes and reparse state from that same handle before creating any child.
For the ledger root, this same-handle readback precedes `.global.lock` creation.

If a private adapter happens to accept a `SECURITY_ATTRIBUTES` input, it may
extract only `lpSecurityDescriptor` for the
`OBJECT_ATTRIBUTES.SecurityDescriptor` pointer. Handle inheritance is governed
separately by omitting `OBJ_INHERIT` and verified with
`GetHandleInformation`; no `SECURITY_ATTRIBUTES` create-path claim or
`bInheritHandle` translation is permitted.

The owner must be the current non-elevated user SID. The DACL must
contain exactly these three explicit, non-inherited `ACCESS_ALLOWED` ACE
subjects and no others; each ACE carries object/container inheritance so the
same policy can be inherited by lock, pending, and final children:

1. current non-elevated user SID: full control;
2. LocalSystem `S-1-5-18`: full control;
3. Builtin Administrators `S-1-5-32-544`: full control.

Reject null/empty root DACLs, inherited root ACEs, deny/callback/object/unknown
ACEs, duplicate subjects, owner mismatch, and any ACE for Everyone, Users,
Authenticated Users, service identities, application packages, or unknown
SIDs. Child readback may contain only inherited allow ACEs resulting from these
three exact root ACEs. Readback must confirm protection, owner, ACE subjects,
ACE types, flags, and rights. Do not broaden or repair the DACL after a failed
readback.

### 4.3 Lock anchor

Create `.global.lock` as the only initial child. Reopen it handle-relative and
verify that it is a regular, non-reparse, zero-byte file with link count `1`,
the same volume identity, an allowed owner/DACL, and the expected final path and
FileId. Any pre-existing child, alternate stream, hardlink, or unknown namespace
entry is `NO-GO`.

Before store import, create the ownership marker beside the ledger root using a
controller-only canonical ASCII name containing a domain-separated run binding,
zero content bytes, link count `1`, no alternate streams, and the exact inherited
child DACL. The marker is not a ledger child and is never visible to the R1B
namespace enumerator.

### 4.4 Process-local constant binding

After importing the module, bind the verified ledger root once to the R1B
private fixed-root constant inside each short-lived harness child before the
first store call or native-backend construction. The binding is immutable for
that child lifetime. Do not restore or transition to the production constant:
after the final store call and result transmission, drop references and exit
the child. The binding must not be accepted from a public API, command line,
environment variable, config file, registry, or log.

The controller must not import the R1B store module or its native-port module.
It independently performs the textual/handle ProgramData and forbidden-root
deny before starting a child, owns only orchestration and run-owned fixture
creation, and cannot silently fall through to a production store constant.

For multi-process cases, the parent sends the raw root and, only when required,
the raw recovery token through an anonymous inherited pipe restricted with an
explicit handle list. Each child
sets its own private process-local constant and immediately drops references to
the raw root message after opening/validating it. When a token is required, use
a mutable pipe buffer and overwrite that buffer on a best-effort basis after
the single call, then drop references and exit the short-lived child. Python or
library copies are not claimed to be zeroized. Pass neither value in process
creation arguments or environment blocks. If the
reviewed implementation has no safe private binding seam, NV1 is `NO-GO` and a
separate authorized code Atomic Unit is required.

## 5. Harness invocation freeze

This R0 does not invent an executable command before an NV1 harness exists.
Exact commands remain `DEFERRED / NO-GO` until a separately reviewed record
pins all of the following:

- absolute Python executable path and SHA-256;
- exact repository checkout HEAD, clean status, working directory, harness
  repository-relative path, blob id and SHA-256;
- Windows argument-vector representation and quoting, with no shell expansion;
- `PREFLIGHT` and `ONE_SHOT` mode names and their exact closed arguments;
- closed exit-code meanings, including success, technical failure,
  not-confirmed Gate, cleanup-not-confirmed, and harness-internal failure;
- proof that no argument or environment entry contains a raw root, token,
  nonce, SID, FileId, private coordinate, or secret.

`PREFLIGHT` is read-only and must perform no temporary/root/marker/lock/file
creation, ACL mutation, native store call, or cleanup. It may establish the
dependency, clean checkout, interpreter/harness hashes, current Gate, known-
folder textual deny, and command readiness. `ONE_SHOT` is the only NV1 native-
validation mode; it runs the frozen ordered cases once after the pre-execution
secretary receipt. It has no retry mode. The working directory is the exact
dependency checkout, never the temporary parent or ledger root.

The foreign/reparse/identity/ADS cleanup-preservation matrix belongs only to
`PREFLIGHT` pure/fake tests over an in-memory private port. These tests assert
that no disposition is requested for an adversarial observation. They do not
create a Windows directory, file, stream, reparse point or hardlink and are not
NV1 native cases. Exact commands remain deferred with the harness command
record rather than being invented here.

Until this command record and the section 11.1 receipt both exist, do not run
`ONE_SHOT` or manually reproduce its intended effects.

## 6. Execution rules

- At `ONE_SHOT` start, re-read the current Gate and require its complete
  identity, revision/digest, scope, expiry and cleanup reservation to be exactly
  unchanged from the section 11.1 receipt, with `state=OPEN`. Derive a local
  monotonic deadline from the Gate's UTC expiry and the current `(UTC,
  monotonic)` clock pair.
- Re-evaluate that exact unchanged `OPEN` Gate, current UTC before expiry and
  current monotonic time before the derived deadline immediately before every
  NV1 case and immediately before every new native, store, lock or fault-seam
  call. This includes read-only observation/identity/enumeration calls,
  `LockFileEx` acquire/contention calls, pending inspection, cleanup calls while
  the Gate remains open, and calls inside a case after its case-level check.
  `UnlockFileEx` is not `LOCK`; it is governed by `RESOURCE_RELEASE` below. A
  case check never substitutes for a call check, and a call cannot be exempted
  by describing it as read-only, diagnostic, idempotent or internal.
- Every call is classified before execution into the closed set `NATIVE`,
  `STORE`, `LOCK`, `FAULT`, `RESOURCE_RELEASE`,
  `IN_FLIGHT_RECONCILIATION`, or `CLEANUP`. Unknown or mixed classification is
  `NO-GO`; there is no call-classification loophole.
  Record the case id, call sequence, Gate exact-match boolean and both UTC/
  monotonic before-deadline booleans without persisting raw host clock internals.
- If any exact-match, state or clock check fails, begin no new case and no new
  ordinary `NATIVE`, `STORE`, `LOCK` or `FAULT` call, and set
  `technical_result=NOT_CONFIRMED`. One native call already in flight may finish.
  Only causally bound, minimum `IN_FLIGHT_RECONCILIATION` calls may then observe
  and truthfully classify that single call; they cannot start a new store
  operation, acquire a new lock, install a fault, retry, or broaden scope.
- `RESOURCE_RELEASE` is a mandatory expiry exception for an exact resource whose
  successful acquisition/allocation and opaque causal resource id were observed
  before Gate failure/expiry. It covers only release ABIs such as
  `UnlockFileEx`, `CloseHandle` and `LocalFree`. It can never acquire/open/read/
  write/rename/delete, create a filesystem disposition, install a fault, or
  retry. Attempt each required release once even after expiry and record its
  causal resource id, attempted/completed/fault state and the resulting
  unreleased-handle/native-allocation counts. Raw handles/pointers remain
  private; the causal id is a per-run nonce-salted domain hash of resource type
  and allocation sequence, not a handle/pointer encoding. A resource returned
  by the one already in-flight call is releasable
  only inside that call's minimum `IN_FLIGHT_RECONCILIATION`, with the same
  observed release facts; it does not broaden `RESOURCE_RELEASE` eligibility.
  A handle created after expiry inside an explicitly reserved `CLEANUP` call
  must be released inside that same causally bound cleanup scope and recorded as
  `CLEANUP`; it cannot be reclassified to widen `RESOURCE_RELEASE`.
- Child/process exit is not a substitute for an observed release call. A release
  fault remains a truthful unresolved count/state even if later process exit
  lets Windows reclaim the resource. Do not retry or retroactively rewrite it
  as release-confirmed.
- Gate scope may explicitly reserve post-expiry `CLEANUP` calls for only this
  run's exact self-created, identity-bound resources/artifacts. Before every
  such call, re-read and exact-match the same cleanup reservation. Under it,
  strict cleanup may continue after expiry. Without it, issue no new explicit
  cleanup native call after expiry. Complete all mandatory `RESOURCE_RELEASE`
  attempts, then allow the short-lived child to exit, preserve the owned outer
  container, record salted bindings, set
  `cleanup_result=PRESERVED_FOR_OWNER_REVIEW`, and request Owner direction. The
  cleanup reservation never authorizes a new test/fault fixture.

- Execute each case once, in order, under the same exact implementation and run
  binding. All native cases use the primary ledger root; no adversarial
  preservation fixture is created. There is no automatic retry, retry loop, or
  retry after an ambiguous native result.
- Capture only public-safe state, reason codes, counts, booleans, schema result,
  implementation/schema hashes, root-binding digest, receipt digests, and
  timings. Redact raw paths, SIDs other than the three policy labels, FileIds,
  security descriptors, handles, and tokens.
- Validate every generated private receipt and public projection against the
  exact local schema and runtime parser.
- In every result assert `receipt_is_authority=false`,
  `consumer_revalidation_required=true`,
  `post_return_state_guaranteed=false`, and all canonical/PASS/latest,
  storage-origin, durability, WORM, owner-death, and R2 authority/effect flags
  are false.
- A native exception escaping the public receipt boundary, schema/runtime
  disagreement, unexplained unknown namespace state outside NV1-09, unexpected
  release uncertainty outside NV1-11, or unexpected side effect is `FAIL`;
  stop subsequent cases and preserve the bounded root for manual review.

## 7. Ordered validation cases

### NV1-01 Empty namespace

Open the pre-provisioned root and global lock, inspect the empty ledger, and
verify an empty valid chain, no pending aggregate, no writes, confirmed release,
and a schema-valid non-authoritative public projection.

### NV1-02 First append

Prepare one synthetic R0/R1A candidate with no audio/media payload, obtain the
raw token only in process memory, append revision 1, and verify `CREATE_NEW`,
file flush/readback, no-replace rename, same-FileId continuity, relative final
reopen, exact canonical bytes, valid chain, known commit, and confirmed release.

### NV1-03 Process restart observation

Terminate the first harness process after confirmed release. Start a fresh
process, privately bind the same root, and verify the exact revision-1 chain
from disk. No in-memory capability or prior diagnostic receipt may authorize
reuse. The raw root is transferred only by the inherited pipe described above.

### NV1-04 CAS mismatch

Submit a synthetic candidate with a deliberately stale CAS expectation. Verify
fail-closed rejection before pending creation, write, flush, or rename. Confirm
that revision 1 and the namespace are unchanged.

### NV1-05 Two-process global lock

Have process A hold the verified whole-file exclusive `.global.lock`. Process B
attempts one immediate acquisition and must receive `LOCK_BUSY` without retry or
write. After both processes exit, start a fresh observer and perform complete
chain/pending reconciliation; do not claim abandoned-owner detection.

### NV1-06 Retained pending

Use the reviewed test-only seam to stop exactly after a new pending wrapper has
been written, file-flushed, read back, and bound to its FileId, but before
rename. Verify an incomplete/not-committed receipt plus sealed recovery receipt,
positive pending count/bytes, `RECOVERABLE` verified pending state, no raw token
disclosure, and no automatic cleanup or promotion.

### NV1-07 Restarted pending inspection

Restart the process and inspect the exact pending file using the sealed recovery
receipt and the raw token retained only by the parent harness memory. Verify
root/key/revision/CAS/payload/token/FileId bindings and a schema-valid
`RECOVERY_AVAILABLE` diagnostic result. A zero-byte, partial, replaced, or
different-FileId pending file must never be reported recoverable.

### NV1-08 Recovery resume

Resume once with the exact token and recovery receipt. Verify pre-rename live
revalidation, same-handle no-replace rename, pending-to-final FileId continuity,
final relative reopen, exact bytes, fresh full-chain derivation, known commit,
confirmed release, and absence of an automatic second write. Restart once more
and verify the resulting chain by observation only.

### NV1-09 Rename completion unknown

Use the reviewed seam to execute the real no-replace rename once, suppress its
completion result, and surface `SYSCALL_COMPLETION_UNKNOWN`. Reconcile the
namespace under the still-held global lock. If exact final identity/content is
observed, preserve the resulting known commit truth; emit
`COMMIT_STATE_UNKNOWN` only when the syscall completion and namespace remain
genuinely ambiguous. No exception may escape and no retry/second rename occurs.

### NV1-10 Returned-true post-rename observation fault

Allow no-replace rename to return true, then inject a failure in final reopen or
readback. Verify a non-escaping `INCOMPLETE` receipt with
`rename_state=RETURNED_TRUE`, `commit_state=KNOWN_COMMITTED`, incomplete resource
observation, and no unverified chain count/digest claim. A fresh short-lived
observer must later derive the actual namespace independently.

### NV1-11 Fault after successful operation release

In separate short-lived children, inject one unlock failure and one close
failure after an otherwise successful observation/append. Verify that technical
namespace/commit facts are not rewritten, the result is downgraded to
`INCOMPLETE`, release state/counts are truthful, and no harness collection keeps
a handle intentionally alive. Do not claim failed close zeroization or recovery.
After each child exits, a fresh child must reacquire the lock and perform full
reconciliation; neither operation is retried. Process exit and later lock
availability do not replace the original release-attempt observation or clear
its unreleased count.

### NV1-12 Complete run-owned cleanup

After the final Gate re-evaluation, and only under an open Gate or its exact
post-expiry cleanup reservation, wait for all worker/store handles to exit and
apply the strict cleanup sequence in section 9 to only the expected primary
ledger artifacts, ownership marker, ledger root and outer container. Verify by
the held temporary-parent handle that the outer name is absent. This case creates no
foreign, reparse, replacement, hardlink or ADS fixture. Any intentional
leftover is prohibited; an unexpected mismatch follows the fail-closed Gate/
Owner-review path rather than being manufactured as a native test.

## 8. Result and stop rules

`technical_result` is one of `PASS`, `FAIL`, or `NOT_CONFIRMED`.

- `technical_result=PASS` requires all twelve cases, schema/runtime parity,
  exact authority flags, the expected technical behavior for deliberately
  injected operation/release faults, `cleanup_result=CLEANED`, every run-owned
  child absent, ledger root absent and outer container absent.
- `technical_result=FAIL` records the first failed case and stops. Do not retry
  the case or reinterpret an ambiguous rename/commit result as success.
- `technical_result=NOT_CONFIRMED` is used when authority, dependency,
  environment, harness, schema, or technical observation is insufficient. It
  is not PASS.

Record `cleanup_result` independently as `CLEANED`,
`PRESERVED_FOR_OWNER_REVIEW`, `FAILED`, or `NOT_CONFIRMED`. Preservation can be
required by a real unexpected mismatch or by Gate expiry without an exact
cleanup reservation, but it can never produce NV1 PASS. Never relabel
preservation as successful deletion or let cleanup state rewrite namespace/
commit truth.

NV1 `technical_result=PASS` is evidence only. It does not authorize production
root provisioning, production execution, canonical PASS/current/latest state,
R2, release, deploy, or Production Activation.

## 9. Strict cleanup

Cleanup is permitted only after every worker child exits and every required
`RESOURCE_RELEASE` call was attempted. Ordinary sessions require confirmed
release and zero unreleased counts. The deliberate NV1-11 release-fault receipt
retains its original unresolved count permanently; process exit does not rewrite
it. After that child exits, a fresh Gate-checked process must independently
acquire the exclusive lock and revalidate the full namespace before cleanup.
That fresh observation proves only that cleanup can proceed without an active
conflict; it is not retroactive release confirmation. An unexpected release
fault outside NV1-11 blocks filesystem disposition and preserves the namespace
for Owner review. Gate expiry follows the reservation rule in section 6. Absent
that reservation, complete mandatory release attempts, issue no new explicit
cleanup call, allow the short-lived child to exit, and preserve the filesystem
namespace for Owner review.

1. Immediately after worker/store exit, close the old ledger-root verification
   handle. Retain only its required parent handles (outer and temporary parent),
   then open a fresh cleanup traversal handle to the ledger root relative to the
   held outer handle. Revalidate the exact root identity before child cleanup.
2. Enumerate the ledger root through that fresh handle with the same bounded
   `NtQueryDirectoryFile` ABI as validation. Before deletion and again during
   cleanup, enumerate streams through bounded native `FileStreamInformation`:
   maximum 16 records and 64 KiB metadata per child. Only the unnamed default
   data stream is allowed. An ADS, truncated record, overflow, or unknown stream
   preserves the root without disposition.
3. Match every child to the exact recorded canonical ASCII name, FileId, final
   path, volume, regular-file/directory type and link count created by this run.
   Unknown, changed, reparse, hardlinked, or additional children stop cleanup.
4. Open each expected file from the fresh root handle using parent-relative
   `NtCreateFile` with desired access
   `DELETE | FILE_READ_ATTRIBUTES | READ_CONTROL | SYNCHRONIZE`, share
   `READ | WRITE | DELETE`, disposition `FILE_OPEN`, non-inheritable handle, and
   options `FILE_OPEN_REPARSE_POINT | FILE_SYNCHRONOUS_IO_NONALERT |
   FILE_NON_DIRECTORY_FILE`. Read back identity/path/link/DACL and stream state
   from that handle. Never follow a reparse target.
5. Delete an accepted child only with `SetFileInformationByHandle`, information
   class `FileDispositionInformationEx` (`21`), and frozen flags exactly
   `FILE_DISPOSITION_FLAG_DELETE` (`0x00000001`). POSIX semantics, on-close,
   ignore-readonly, force-image-section, pathname and shell fallbacks are
   prohibited. Close the handle, then re-enumerate to prove the one expected
   namespace removal. Delete pending/final files individually and
   `.global.lock` last.
6. After exact ledger-root emptiness, close the fresh cleanup traversal handle.
   Retain the outer handle as the root's needed parent (and the temporary-parent
   handle for the later outer stage).
   Reopen the ledger root parent-relative from that outer handle with directory
   `NtCreateFile` access `DELETE | FILE_READ_ATTRIBUTES | READ_CONTROL |
   SYNCHRONIZE`, share `READ | WRITE | DELETE`, disposition `FILE_OPEN`, and
   options `FILE_DIRECTORY_FILE | FILE_OPEN_REPARSE_POINT |
   FILE_SYNCHRONOUS_IO_NONALERT`. Revalidate FileId/path/volume/DACL/streams,
   apply class 21 with flags `0x00000001`, close the delete handle, and
   re-enumerate the outer container to prove root absence.
7. Delete the exact ownership marker by the file ABI only after ledger-root
   absence. Re-enumerate and require outer-container emptiness. Then close the
   old outer verification handle, retaining only the temporary-parent handle.
8. Reopen the outer container parent-relative from the held temporary-parent
   handle with the directory delete ABI from step 6, revalidate exact identity,
   apply class 21 with flags `0x00000001`, close, and re-enumerate the temporary
   parent to prove the outer name absent. Finally close the temporary-parent
   handle. Never disposition, clean, or otherwise mutate the `GetTempPath2W`
   parent itself.

Do not use recursive deletion, wildcard deletion, `Remove-Item -Recurse`,
`rm -rf`, `rmdir /s`, broad temp cleanup, shell-composed paths, or cleanup of a
parent directory. Do not retry a failed delete. On any mismatch or failure,
leave the bounded root in place, record only its root-binding digest and the
cleanup state, and request manual Owner review. Never print the raw root.

No actual NV1 case intentionally creates an artifact that cleanup is expected
to preserve. Foreign/reparse/identity/ADS preservation behavior is tested only
by the section 5 pure/fake matrix. NV1 `technical_result=PASS` requires the
primary root, marker and outer container all absent; there is no automatic
second cleanup attempt.

## 10. Explicitly prohibited effects

NV1 must not install or update software, access the network, access E:, read or
write private voice/media, load or run an AI/audio model, process audio, launch
REAPER/iZotope or another application, touch a production root, change a
production ACL, purchase credits, call a provider, release, deploy, or activate
Production. No retry is authorized after a native or cleanup failure.

## 11. Secretary delivery records

Omit raw roots, parent paths, tokens, nonces, handles, FileIds, SIDs, SDDL,
machine/volume identifiers, private coordinates, and secret values from both
records.

### 11.1 Pre-execution delivery receipt (hard Gate)

This record is sent and read back before `ONE_SHOT` or any temporary/native
mutation. It contains:

- project: `BAI VIDEO PRODUCTION`;
- task / Atomic Unit: `TASK-041 / R1B NV1`;
- runbook repository-relative path, containing Git commit SHA, Git blob id and
  file SHA-256;
- dependency: `PR 270 / e337759`, ancestry result and exact intended test HEAD;
- Codex task/thread id, source message id and delivery message id;
- `sent_at` as an RFC 3339 UTC timestamp;
- exact recipient role/address label;
- delivery status and independent readback status;
- secretary receipt id/digest and `received_at` UTC;
- Owner sleep Gate id, authority-record revision/digest, scope, opening/expiry
  timestamps, current state, and exact `cleanup_after_expiry` reservation state;
- pure/fake foreign/reparse/identity/ADS preservation test command, source/test
  hashes and PASS result;
- reviewed harness path/blob/SHA-256 and frozen-command-record id/digest, or an
  explicit `NOT_READY` that keeps NV1 `NO-GO`;
- statement that native/temp mutation before this receipt was `NOT_EXECUTED`.

Only `delivery_status=DELIVERED` and `readback_status=CONFIRMED`, with all exact
bindings present and the Owner sleep Gate still open, release the pre-execution
Gate. A draft, queued, sent-only, unread, mismatched or stale record is `NO-GO`.

### 11.2 Post-NV1 outcome memo

After `ONE_SHOT` stops, send a separate outcome memo containing:

- reference to the section 11.1 secretary receipt id/digest;
- exact tested HEAD, clean/dirty-state result, Python executable SHA-256,
  harness blob/SHA-256, working directory binding and frozen command-record id;
- Owner sleep Gate exact-match/state observed at `ONE_SHOT` start, immediately
  before every NV1 case, and immediately before every native/store/lock/fault
  call, including call classification/sequence and UTC/monotonic before-expiry
  booleans. This includes read-only observations, lock acquire/contention and
  pending inspection; unlock is reported only as `RESOURCE_RELEASE`;
- any expiry/closure point, in-flight-call truthful reconciliation result, and
  causal call id, plus every reserved-cleanup-call exact-match result and whether
  the exact post-expiry cleanup reservation was used;
- operator role and non-elevated-token confirmation;
- Windows version/architecture and `GetTempPath2W`/LocalAppData containment,
  ASCII, fixed-local NTFS, no-reparse and no-fallback results;
- production/ProgramData/repository/project/private/E: textual and handle deny
  results, explicitly stating that E: was not probed;
- protected atomic-create DACL/owner readback, outer marker, lock zero-byte,
  hardlink-count-one, ADS-empty and namespace preflight results;
- per-run salted machine, volume, outer-container and ledger-root binding
  digests, with raw identifiers and nonce `NOT_PERSISTED`;
- private/public schema SHA-256 and mirror-equality result;
- NV1-01 through NV1-12 technical result, reason codes, receipt/public digest,
  phase facts and duration for each case;
- two-process lock result and explicit retry count `0`;
- pending/recovery and rename FileId-continuity results without FileId values;
- completion-unknown, returned-true observation-fault and unlock/close-fault
  decision/commit/release observations;
- every `RESOURCE_RELEASE` call (`UnlockFileEx`, `CloseHandle`, `LocalFree` or
  another reviewed release ABI), its opaque causal resource id, pre-expiry
  acquisition binding, attempted/completed/fault state, and before/after
  unreleased counts; separately identify any release performed only inside the
  one in-flight call's reconciliation;
- all non-authority/effect flags and schema/runtime parity result;
- unreleased handle/native allocation counts, followed by child-exit and fresh-
  process reconciliation observations without treating child exit as release
  confirmation or claiming zeroization;
- per-child class-21 cleanup observations, bounded ADS checks, old-handle close
  order, cleanup-local handle release observations, and outer/marker/root
  absence; on a real unexpected mismatch or
  unreserved expiry, the salted preserved primary/outer binding and Owner-review
  requirement instead;
- `technical_result`: `PASS`, `FAIL`, or `NOT_CONFIRMED`;
- separate `cleanup_result`: `CLEANED`, `PRESERVED_FOR_OWNER_REVIEW`, `FAILED`,
  or `NOT_CONFIRMED`;
- prohibited-effect audit: install/network/E:/private/audio/model/application/
  production/release/deploy all `NOT_EXECUTED`;
- unresolved Gate/finding and the exact next authorized action.

Both secretary records are evidence transmission only. Neither broadens Owner
authority nor converts NV1 evidence into canonical Product state.
