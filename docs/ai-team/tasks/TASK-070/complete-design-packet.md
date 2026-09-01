# TASK-070 — Installer Authority Baseline, Lease and Descriptor Pair

Status: `DESIGN_COMPLETE / DEV-4 / SOURCE_START0`

Design identity: `TASK070-PTD-INSTALLER-AUTHORITY-PAIR-V1`

Canonical design base: `origin/main@35cdf1ad475633dcf035e0616e979b5a8fde0c88`

Owner allocation: `2026-09-01 / Platform Trust & Delivery / Design B`

## 1. Decision

TASK-070 owns one Product-private installer authority transaction that binds an
installer-selected root, one secure operation lease and the exact
`bridge-instance.json` / `bridge-owner.json` pair. One immutable
`PAIR_TERMINAL_V2` durably binds both documents' exact opened bytes, physical
identities, security state and one trusted install operation, but is not
current authority by itself. Consumer authority exists only as a private
one-use `INSTALLATION_PAIR_READBACK_V2` issued after terminal pinned readback
and a post-terminal same-operation currentness attestation.

The two compatibility documents are never treated as a transaction merely
because their fields or hashes agree. They are created only with no-replace
publication, are not rewritten during repair or upgrade, and are never
automatically deleted or rolled back. Repair verifies the original pair;
upgrade publishes a separate immutable installation-revision record. A
portable rebind provisions a new target pair under a separate authorized root
and binds its predecessor; it never silently adopts a moved/copied directory.

TASK-070 composes TASK-068 immutable I/O and TASK-072 one-shot operation
authority. It does not broaden either Task. TASK-068 receipts remain I/O
evidence with `authority_created=false`; TASK-072 creates the live one-shot
machine capability but does not decide install-root or pair semantics.

## 2. Why this is a separate Task

Current `montage_learning_installation.py` and the TASK-058 owner loader expose
separate path-based operations:

- descriptor existence/read precedes an unbound `AtomicJsonWriter` replace;
- descriptor and owner are discovered through separate reads;
- readback locking uses a generic path lock;
- temporary handles are closed before path-based publication;
- directory durability errors may be ignored;
- fresh/update rollback may delete or overwrite a foreign replacement;
- descriptor, owner and rollback preimages are not one strict opened snapshot.

TASK-063 owns installer semantics and packaging, while TASK-058 owns File
Bridge semantics. A shared physical authority transaction is a new bounded
responsibility and must not be hidden in either existing owner module.

## 3. Responsibility and non-responsibility

TASK-070 owns:

- private attestation of one pre-created selected-install ancestor chain;
- exact install-root/data/bridge/authority-directory physical and DACL binding;
- secure installer-operation lock acquisition for initial and existing lock
  states;
- the one-use live pair-plan capability consumed under that lease;
- strict opened-snapshot reading of descriptor and owner together;
- first-provision no-replace publication of the two compatibility documents;
- immutable PREPARED/phase/terminal records at exact operation coordinates;
- terminal exact readback and public body/path-free projection;
- immutable repair, upgrade-revision and portable-rebind lineage;
- crash classification, preservation and explicit recovery boundaries;
- versioned non-authoritative fixtures for TASK-063 and TASK-072 consumers.

TASK-070 does not own:

- installer destination selection, installer UI, payload placement or package
  digest policy (TASK-063);
- File Bridge directories, delivery/import, owner semantics, canonical
  admission or Profile data (TASK-058/TASK-067/TASK-069);
- generic secure JSON/lock/no-replace primitives (TASK-068);
- one-shot ticket issuance or config publication (TASK-072);
- Human authorization (TASK-071);
- legacy data migration, activation or activation history (TASK-061);
- preference promotion/source state (TASK-060);
- D2S command execution or PL orchestration (TASK-036/TASK-065);
- directory-tree rename, mutable pointer/current selection, same-path mutable
  JSON CAS, automatic rollback, repair by deletion, uninstall cleanup or GC;
- Release, Deploy, Production Activation, paid Provider, private-media upload,
  external-account mutation or real install execution.

## 4. Artifact/phase dependency graph

The dependency graph is artifact-based so design and fixtures can proceed
without inventing a Task cycle:

```text
TASK-068 IMMUTABLE_SECURE_IO_V1 canonical receipt
    -> TASK-070-A BASELINE_AND_PAIR_FIXTURE_V1

TASK-063 PRETERMINAL_SELECTED_INSTALL_PLAN_ABI_V1
TASK-072-A OP_TICKET_CORE_V1
TASK-070-A BASELINE_AND_PAIR_FIXTURE_V1
    -> TASK-070-B FIRST_PAIR_EFFECT_V1

TASK-070 PAIR_TERMINAL_V2 + private INSTALLATION_PAIR_READBACK_V2
    -> TASK-063 INSTALLATION_READBACK_V2

TASK-070 PAIR_TERMINAL_V2 + private INSTALLATION_PAIR_READBACK_V2
TASK-063 INSTALLATION_READBACK_V2
    -> TASK-072-B INSTALLED_INSTANCE_PROFILE_BINDING_V1

TASK-070 PAIR_TERMINAL_V2 + private INSTALLATION_PAIR_READBACK_V2
TASK-063 INSTALLATION_READBACK_V2
    -> TASK-060 / TASK-061-A / TASK-036 / TASK-065 installed bindings
```

TASK-063's preterminal plan is a design/fixture ABI and is not a completed
install receipt. TASK-072-A is the broker core/fixture phase, not an installed
binding. TASK-070 may freeze fixtures before either producer effect exists;
`PAIR_TERMINAL_V2` cannot be emitted until all exact producers are canonical.

TASK-068 Draft PR `#472` remains noncanonical until merged with its completion
receipt. TASK-072 Draft design PR `#475` creates no broker implementation.
Therefore TASK-070 source/native effects remain `DEPENDENCY_NC` even after this
design freezes.

## 5. Design PR and future implementation scope

This design PR may change exactly:

- `docs/ai-team/tasks/TASK-070/complete-design-packet.md`

After C/H=0 and Judge PASS, the future TASK-070 implementation Task may change
exactly:

- `src/ai_video_production/installer_authority.py`
- `src/ai_video_production/installer_authority_windows.py`
- `schemas/installer-authority-baseline.schema.json`
- `schemas/installer-successor-reservation.schema.json`
- `schemas/installer-descriptor-pair-terminal.schema.json`
- `schemas/installer-installation-revision.schema.json`
- `src/ai_video_production/schema_resources/installer-authority-baseline.schema.json`
- `src/ai_video_production/schema_resources/installer-successor-reservation.schema.json`
- `src/ai_video_production/schema_resources/installer-descriptor-pair-terminal.schema.json`
- `src/ai_video_production/schema_resources/installer-installation-revision.schema.json`
- `tests/test_task070_installer_authority.py`
- `tests/test_task070_installer_authority_windows.py`
- `tests/test_task070_installer_authority_packaging_contract.py`
- `tests/fixtures/task070/**`
- `docs/ai-team/tasks/TASK-070/**`

Changes to TASK-058, TASK-063, TASK-068, TASK-072, installer scripts,
`atomic.py`, packaging, shared current-state/task-index/roadmap, CHANGELOG or
another Task require their owning Task's separate exact amendment and a fresh
overlap/sole-writer check.

## 6. Production composition and threat boundary

Production fixes internally:

- TASK-068 `SecureAuthorityIO` implementation/version;
- TASK-072 broker/profile implementation/version;
- native Windows file/security backend;
- trusted clock and boot/session coordinate;
- Product/installer package/build digests;
- install security policy version;
- descriptor and owner contract adapters.

No argv, JSON, public plan, serialized receipt, environment, current working
directory, registry fallback, dependency injection, monkeypatch, hook or
failure injector may select those implementations. Test backends are reachable
only through a non-Production composition.

The v1 boundary protects against public/caller construction, copied files,
path/link races and separately launched same-user processes that do not possess
the inherited TASK-072 channel or compromise a trusted process. It does not
claim resistance to administrator compromise or arbitrary same-user process
injection/VM access into the Product/broker. The unsupported stronger attacker
model is `NOT_SUPPORTED_V1` and cannot be promoted to native PASS.

## 7. Pre-created layout and pinned baseline

TASK-063's trusted installer creates, before invoking TASK-070, only these exact
directories under its selected root:

```text
<selected-install-root>/
`-- data/
    |-- .bvp-installer-authority/
    `-- montage-learning-bridge/
```

TASK-070 never accepts a caller path and never creates these directories. The
private preterminal plan supplies live directory handles/identities from the
trusted installer. TASK-070 independently opens and pins the selected root,
`data`, `.bvp-installer-authority` and `montage-learning-bridge`, then proves:

- exact contained coordinate and component spelling;
- regular directory type, no symlink/reparse/mount substitution;
- nonzero stable physical identity before/after every namespace effect;
- expected installer owner SID and security descriptor policy;
- no untrusted write/delete/change-owner/change-DACL access;
- expected package/build/session and selected-install operation;
- no fixed ProgramData, environment, CWD or raw external-root fallback.

An absent directory, case/short-name alias, unknown nonempty directory, DACL
drift or identity drift is STOP. Directory creation/repair belongs to the
trusted TASK-063 installer step and is not inferred from TASK-070 evidence.

## 8. Versioned ports

### 8.1 `PRETERMINAL_SELECTED_INSTALL_PLAN_ABI_V1`

Private TASK-063 producer input. It binds:

- random selected-install operation identity;
- Product/package/installer build and payload-tree digest;
- intended install instance or explicit first-provision intent;
- exact selected-root/data/authority/bridge handles and identities;
- owner SID/session/logon LUID and security-policy version;
- exact pair action, expiry, invocation budget one;
- expected predecessor pair/revision/rebind receipt when applicable;
- Task-072 config-parent binding and stable consumer operation key.

Its public projection is display evidence with `authority_created=false`; a
caller path or reconstructed mapping cannot create a baseline.

### 8.2 `INSTALL_AUTHORITY_BASELINE_V1`

Private live baseline returned only after section 7 attestation. It retains all
four directory handles through lease, publication, terminal readback,
post-terminal currentness attestation and consumer handoff and
binds their physical/security snapshots to the Task-063 plan and TASK-072
ticket. Public output contains only opaque hashes, stable codes and
`authority_created=false`.

### 8.3 `INSTALL_OPERATION_LEASE_V1`

The fixed lock is under `.bvp-installer-authority` and remains permanently. An
initial lock is created with TASK-068 secure initial semantics: `CREATE_NEW`,
no-follow/open-reparse, one-byte content, regular file, `nlink == 1`,
non-inheritable live handle and post-create security/identity verification. An
existing lock is opened no-follow, validated and locked on the same physical
handle. A create-race loser is freshly classified and fails; auto retry as
existing is forbidden.

The live lease binds baseline, Task-072 operation/ticket, Product process,
thread ownership, action, build, boot/session and exact lock identity. Copy,
pickle, dataclass reconstruction or a public lock receipt cannot acquire it.

### 8.4 `INSTALL_DESCRIPTOR_PAIR_PLAN_V2`

Private Task-070 plan, verified from the Task-063 preterminal plan and live
TASK-072 `INSTALL_AUTHORITY_PAIR_WRITE` ticket. Closed fields bind:

- action: `FIRST_PROVISION`, `ADOPT_EXISTING`, `VERIFY_REPAIR`,
  `PUBLISH_INSTALL_REVISION`, or `PORTABLE_REBIND`;
- stable `consumer_operation_key`, random operation ID and revision;
- exact install root baseline and install instance;
- descriptor/owner contract versions and exact canonical body digests;
- expected descriptor/owner absence or predecessor bytes/identities;
- expected predecessor terminal/revision/rebind identity;
- exact operation-independent successor reservation coordinate and lane policy;
- package/build/backend/security/clock/session identities;
- exact immutable PREPARED/phase/terminal coordinates;
- invocation budget one and bounded expiry.

Public plan objects, hashes, confirmation strings and module tokens are audit
only. An internally fixed verifier over the complete semantic fingerprint plus
the live Task-072 channel is required.

### 8.5 `SUCCESSOR_RESERVATION_V1`

Every lineage-producing action acquires an immutable fork fence before
`PAIR_PREPARED_V2`. The reservation coordinate is deterministically derived
from the exact predecessor physical/durable identity, the closed lineage lane
and the only admissible successor sequence. It never contains the random
operation ID, ticket ID, build digest or caller-selected coordinate. A genesis
pair has no predecessor, so its coordinate is derived from the pinned selected
root identity, install instance and fixed `PAIR_GENESIS` lane.

The closed lane policy is:

| Action/lane | Reservation basis | Policy |
|---|---|---|
| `FIRST_PROVISION / PAIR_GENESIS` | pinned root identity + install instance | exactly one pair successor |
| `ADOPT_EXISTING / PAIR_ADOPTION` | trusted predecessor receipt + simultaneously opened pair identities | exactly one adoption terminal |
| `PUBLISH_INSTALL_REVISION / REVISION` | exact predecessor revision/terminal identity + predecessor revision + 1 | exactly one direct successor; gap and fork forbidden |
| `PORTABLE_REBIND / REBIND` | exact predecessor pair/rebind terminal identity | exactly one destination successor |
| `VERIFY_REPAIR / OBSERVATION` | no lineage successor | multiple sequential read-only observations allowed; no reservation or new terminal |

TASK-068 publishes the reservation no-replace and performs pinned exact
readback. Its body binds the winning operation, expected successor body digest,
predecessor, lane, revision, baseline, build/backend/session and self-hash, but
the coordinate remains operation/build independent. An existing reservation is
never replaced or deleted. Only the exact already committed terminal bound by
that reservation may be classified `DUPLICATE`; a different body, operation,
build or destination is `SUCCESSOR_COLLISION`. A reservation without its exact
terminal is `RECOVERY_REQUIRED`, not an invitation to retry, adopt or infer a
winner. This closes forks without mutable CAS, a current pointer or a latest
scan.

### 8.6 `PAIR_PREPARED_V2` and immutable phase events

TASK-070 publishes PREPARED through TASK-068 trusted immutable publication at
the exact plan coordinate before touching either compatibility target. Later
events are separate immutable no-replace documents:

- `DESCRIPTOR_PUBLISHED`;
- `OWNER_PUBLISHED`;
- `PAIR_READBACK_VERIFIED`;
- `PAIR_TERMINAL`.

Every event binds the exact predecessor digest/identity, operation, action,
baseline, target pre/post identities, canonical hashes, Task-072 ticket event,
build/backend/session and self-hash. TASK-070 never mutates a phase file,
selects a highest revision or scans for current state.

### 8.7 Compatibility descriptor and owner documents

For first provision only, TASK-070 publishes the closed TASK-063 descriptor and
TASK-058 owner documents at their fixed compatibility names through TASK-068
raw no-replace I/O under the pinned Bridge root. TASK-068 publication receipts
are I/O evidence only. TASK-070 binds the expected documents before calling the
primitive and reopens both afterward.

The descriptor binds the stable install instance, exact relative Bridge path,
initial installer package/build, trusted creation time and self-hash. The owner
document binds the same instance, exact Task-058 contract/profile, production
path claim, current pinned root identity and self-hash.

Repair and same-root upgrade never replace either document. Upgrade state is a
separate `INSTALLATION_REVISION_V1`. A changed fixed target, identical target,
same-body/different-inode target or second first-provision attempt is a
collision unless the exact already committed terminal is supplied for a
read-only `VERIFY_REPAIR`.

`ADOPT_EXISTING` is allowed only for an exact predecessor installation receipt
that already binds both opened bodies/identities and package provenance. It
publishes no compatibility file; it publishes a new pair terminal binding the
existing pair. Content equality or a caller-provided historical receipt is not
sufficient.

### 8.8 `PAIR_TERMINAL_V2`

TASK-070 may publish the durable terminal only while it simultaneously holds
both opened target handles and verifies:

- strict canonical bytes and schema semantics from those handles;
- descriptor and owner install-instance equality;
- fixed Bridge relative path and Product/contract/profile values;
- descriptor/owner self-hashes;
- exact file identities, regular type, `nlink == 1`, no reparse;
- exact ancestor/security baseline and live lease currentness;
- expected PREPARED/phase chain and Task-072 operation;
- post-read namespace identities while both handles remain live.

The terminal binds raw/canonical hashes, physical identities, security digests,
operation/revision/predecessor, successor reservation, package/build/backend/
session, exact phase events and a self-hash. It is published no-replace at the
exact trusted plan coordinate and read back through TASK-068 while all baseline,
lease and pair handles remain live. It selects no global current/head and alone
has `authority_created=false`.

After terminal pinned readback, the same operation must revalidate the live
lease handle, every pinned ancestor identity/DACL, both target namespace
identities, and both still-open target `fstat` identities/bytes. No durable
publication is allowed after this final check. A mismatch preserves the
terminal and all files, returns `PAIR_CURRENTNESS_STOP`, and creates no private
consumer readback or downstream effect.

The public projection exposes only opaque hashes, schema/action/status,
`connector_enabled=false`, `activation_authorized=false`,
`authority_created=false` and `currentness_selected=false`. Absolute paths,
SIDs, DACLs, file IDs, bodies and OS errors remain private.

### 8.9 `INSTALLATION_REVISION_V1`

A repair/upgrade that changes installer payload/build publishes one immutable
revision record bound to the stable pair terminal and prior exact revision.
The descriptor and owner are byte/identity unchanged. The trusted TASK-063
operation supplies the exact revision coordinate; TASK-070 never scans or
selects latest. The operation-independent `REVISION` successor reservation is
acquired before revision PREPARED. Fork, gap, stale predecessor or duplicate
coordinate is STOP.

### 8.10 `PORTABLE_REBIND_V1`

Portable rebind is a distinct operation against a new, pre-created and empty
selected target. It requires the exact predecessor pair terminal, TASK-063
rebind plan, TASK-072 ticket and the predecessor's single `REBIND` successor
reservation. It publishes a new no-replace compatibility
pair and terminal at the new root, binding the predecessor and new physical
root/security baseline.

A copied/moved directory that already contains target files is not implicitly
rebound. Same bytes with different file IDs, the same instance at an unrelated
root, multiple possible predecessors or missing source readback is STOP. Source
data and old pair/terminal remain preserved; copy/migration and old-root
revocation belong to TASK-061 or another explicit Task.

### 8.11 `INSTALLATION_PAIR_READBACK_V2`

For the creating operation, TASK-070 issues this private in-process one-use
object only after the section 8.8 post-terminal check, while the lease, pinned
ancestors and both target handles are still live. For a later authorized
consumer, TASK-070 reads the exact consumer-supplied terminal coordinate, pins
all ancestors, opens descriptor and owner no-follow, holds both handles
together, performs one bounded read per handle, parses/hashes those same bytes,
pins the terminal readback, then performs the same final lease/ancestor/DACL/
namespace/open-handle currentness check immediately before issuing the object.
It never calls `Path.read_text`, performs separate close/reopen equality reads,
or trusts a TASK-058 public loader result as authority.

The private readback binds pair terminal, reservation, bodies, identities,
baseline, live-handle currentness and exact consumer operation for
TASK-063/TASK-072. It is nonserializable, noncopyable, consumed once and burned
on success or exception. The durable terminal and public receipt are
body/path-free audit evidence only and cannot substitute for it.

### 8.12 Early fixture contract

`tests/fixtures/task070/installer-authority-pair-v1/**` contains versioned
non-authoritative fixtures for all ports/actions. Each declares:

- `fixture_only=true`;
- `authority_created=false`;
- `native_effect_executed=false`;
- fixed fake root/instance/build/hash/identity values;
- exact expected public schemas;
- negative vectors for wrong action, pair, predecessor and state.

TASK-063 and TASK-072 may compile against these fixtures. Fixture PASS cannot
satisfy installer, packaged, native, E2E, activation or Production gates.

## 9. Strict JSON and size policy

All authority records use TASK-068 strict bounded UTF-8 parsing before semantic
validation or hashing. Compatibility descriptor and owner documents are also
read through the same strict opened-snapshot pipeline. Reject:

- duplicate keys at every depth, equal or different;
- NaN, Infinity and negative Infinity;
- BOM, trailing data, invalid UTF-8 and disallowed controls;
- non-built-in JSON values;
- oversized bytes, strings, depth, nodes, members and items;
- unknown/missing fields, wrong exact types and noncanonical writer output.

Raw opened bytes hash, canonical parsed hash, physical identity and security
digest remain one sealed private snapshot. Parser failure is body-free effect
zero. Ambiguous files are preserved and never repaired, rewritten or deleted.

## 10. Pair operation state machine

```text
REQUESTED (public audit only)
  -> AUTHORIZED (Task-063 private plan + Task-072 live ticket)
  -> BASELINE_PINNED
  -> LEASED
  -> SUCCESSOR_RESERVED (immutable fork fence; lineage actions only)
  -> PREPARED (immutable and durable)
  -> TARGETS_CLASSIFIED
       -> DESCRIPTOR_PUBLISHED   [FIRST_PROVISION / PORTABLE_REBIND only]
       -> OWNER_PUBLISHED        [FIRST_PROVISION / PORTABLE_REBIND only]
       -> PAIR_READBACK_VERIFIED
       -> PAIR_TERMINAL_DURABLE
       -> POST_TERMINAL_CURRENTNESS_ATTESTED
       -> PRIVATE_PAIR_READBACK_ISSUED

VERIFY_REPAIR
  -> EXACT_COMMITTED_TERMINAL_PINNED
  -> POST_TERMINAL_CURRENTNESS_ATTESTED
  -> PRIVATE_PAIR_READBACK_ISSUED (no new lineage successor)

ADOPT_EXISTING
  -> SUCCESSOR_RESERVED
  -> PREPARED
  -> PAIR_READBACK_VERIFIED
  -> PAIR_TERMINAL_DURABLE
  -> POST_TERMINAL_CURRENTNESS_ATTESTED
  -> PRIVATE_PAIR_READBACK_ISSUED or exact committed-event DUPLICATE

PUBLISH_INSTALL_REVISION
  -> SUCCESSOR_RESERVED
  -> REVISION_PREPARED
  -> REVISION_TERMINAL
```

Rules:

1. Public requests cannot advance state or select root/action/revision.
2. The lease is acquired before reservation/PREPARED and held through terminal
   readback, final currentness attestation and private consumer handoff.
3. Every lineage action acquires its operation-independent no-replace successor
   reservation before PREPARED; a collision never falls through to execution.
4. PREPARED is durable before either compatibility namespace effect.
5. First provision requires both targets absent at its authorized snapshot.
6. Each no-replace publication is followed by exact same-operation identity
   readback and an immutable phase event.
7. Durable terminal authority remains zero until its pinned readback is followed
   by the post-terminal lease/ancestor/DACL/namespace/open-handle check and the
   private one-use readback is issued. A one-sided pair is never a partial PASS.
8. Success, exception, timeout, cancellation or crash burns the Task-072 ticket.
9. A nonterminal operation with a reservation or target effect is
   `RECOVERY_REQUIRED` and is
   preserved. V1 performs no automatic retry, adoption, rollback or deletion.
10. A pre-reservation failure may retry only after TASK-072 accepts an exact durable
   no-effect reconciliation and TASK-063 issues a new predecessor-bound plan.
11. `DUPLICATE` is valid only for the same committed terminal/event with the
     same bodies and physical identities. Equality alone is insufficient.

## 11. Publication sequence

1. Receive the live private Task-063 plan and TASK-072 ticket.
2. Pin/attest the four pre-created directories and build the private baseline.
3. Acquire the exact existing/initial installer-operation lease.
4. Revalidate plan, ticket, baseline, backend, clock and package currentness.
5. For each lineage action, derive, publish no-replace and pin-read the exact
   operation-independent `SUCCESSOR_RESERVATION_V1`; collision stops.
6. Publish/read back PREPARED through TASK-068 immutable I/O.
7. Classify both target names and expected predecessor state under the lease.
8. For first/rebind, canonicalize bounded documents and publish the descriptor
   no-replace through TASK-068; reopen and publish its phase event.
9. Revalidate descriptor, owner absence, ancestors, DACL, plan and ticket.
10. Publish owner no-replace; open descriptor and owner together and publish its
   phase event.
11. Perform pair semantic/identity/security readback while holding both handles.
12. Publish/read back `PAIR_READBACK_VERIFIED`, then `PAIR_TERMINAL_V2`, while
    retaining the lease, all pinned ancestors and both opened pair handles.
13. After terminal readback, revalidate the lease handle, every ancestor
    identity/DACL, both target namespace identities and both opened-handle
    identities/bytes. Publish nothing after this check.
14. If and only if step 13 passes, issue the private one-use readback and its
    body/path-free public audit projection to the exact live consumer.
15. Release handles/lease and burn/close the one-shot ticket on every exit path.

Operation-owned temporary files and directory durability are entirely TASK-068
I/O responsibilities. TASK-070 never closes and later reopens a temporary path,
never unlinks a foreign temp and never suppresses file/directory durability
failure. Published descriptor/owner/phase/terminal artifacts are preserved.

## 12. Fault and recovery policy

| Seam | Result | Recovery/effect rule |
|---|---|---|
| Before authorization/baseline | `REJECTED` | path/body/lock/config/effect zero |
| Baseline or DACL drift | `SECURITY_STOP` | no target effect; preserve all files |
| Lock create/open race | `LOCK_COLLISION` | race loser fails; auto retry zero |
| Successor reservation collision | `SUCCESSOR_COLLISION` | winner preserved; PREPARED/target effect zero |
| Crash after reservation | `RECOVERY_REQUIRED` | reservation preserved; blind retry/adopt/delete zero |
| PREPARED publish/readback failure | fail/completion unknown | targets untouched; exact record preserved |
| Descriptor target appears | `PAIR_COLLISION` | winner preserved; owner/terminal zero |
| Crash after descriptor | `RECOVERY_REQUIRED` | descriptor preserved; owner/terminal authority zero |
| Owner target appears | `PAIR_COLLISION` | both names preserved; terminal authority zero |
| Crash after owner | `RECOVERY_REQUIRED` | pair preserved but untrusted until explicit recovery |
| Pair readback/terminal fsync failure | fail/completion unknown | no PASS/DUPLICATE; preserve evidence |
| Last pair check through terminal readback swap | `PAIR_CURRENTNESS_STOP` | terminal/files preserved; private readback/consumer effect zero |
| Post-terminal target/ancestor/DACL/lock swap | `PAIR_CURRENTNESS_STOP` | terminal/files preserved; private readback/consumer effect zero |
| Upgrade revision collision/fork | `REVISION_STOP` | pair/revisions preserved; no current selection |
| Portable target nonempty/copied | `REBIND_STOP` | source/target untouched |
| Cleanup failure | stable warning only | cleanup never determines correctness |

V1 deliberately stops on a crash-created one-sided or terminal-missing pair.
Automatic forward recovery would require a separately versioned TASK-072
recovery action that binds the exact partial identities; it must not be inferred
from this design or a public receipt.

## 13. Installer/UI operation flow

TASK-070 has no standalone settings page. The TASK-063 installer owns the
visible flow and may display only bounded Japanese status:

- `インストール先を確認しています`
- `学習データ領域を準備しています`
- `インストール情報を確認しています`
- `インストール情報を安全に確定しました`
- `安全のため処理を停止しました`
- `以前の処理状態を確認する必要があります`

No UI shows/edits absolute internal paths, file IDs, SIDs, DACLs, ticket,
nonce, hashes, backend or timestamps. A nonterminal pair offers no blind retry,
delete or overwrite button. It routes to bounded repair/recovery guidance.

## 14. Privacy and public diagnostics

Public errors, receipts, UI, logs and stdout contain only stable codes, opaque
operation/instance IDs, action/status, hashes/counts and authority booleans.
They contain no absolute path, username/SID, DACL, native handle/file ID, JSON
body, package path, command line, OS error text, secret or offending value.

`connector_enabled=false`, `activation_authorized=false` and
`authority_created=false` are mandatory public defaults. A public pair receipt
cannot authorize connector execution, Profile publication or activation.

## 15. Negative matrix

Every negative separately asserts descriptor delta, owner delta, phase/terminal
delta, child/process delta, activation/config/history delta and unrelated-file
overwrite/delete delta.

### T70-AUTH

- direct/public plan, dataclass, mapping, self-hash or module token;
- copy/replace/subclass/duck type/pickle/deserialization;
- caller root/action/revision/ID/time/backend/clock/hook;
- wrong Task-063 plan, Task-072 ticket, build, instance, session or operation;
- fixture or Task-068 public receipt promoted to pair authority.

Expected: baseline/lease/pair capability zero and filesystem effect zero.

### T70-BASELINE

- relative/raw external root, environment, CWD and fixed ProgramData fallback;
- install/data/authority/bridge ancestor stat-open/post-open swap;
- reparse/symlink/mount/case/short-name alias and unexpected directory;
- DACL/owner drift before lease, each publish and final readback;
- mixed install root, package, user/session or authority directory;
- absent or unknown-nonempty pre-created directory.

Expected: no lock/target/phase/terminal effect and body/path-free failure.

### T70-LOCK

- initial concurrent create, absent-then-appears and create-race loser;
- existing lock symlink/reparse/hardlink/nonregular/wrong-size;
- lock target or ancestor replacement before/after acquisition;
- copied public lock receipt, concurrent operation A/B and phase backend swap.

Expected: at most one live lease; loser/replay effect zero; lock is never
deleted or recreated automatically.

### T70-PAIR

- descriptor/owner absent-to-appears identical/different;
- only one target exists, mixed generation or cross-instance pair;
- same bytes/different inode at stat-open/read-post seams;
- descriptor/owner swap before first publish, between publishes, before
  terminal, during terminal publication/readback and after terminal;
- target hardlink/reparse/nonregular/nlink drift;
- identical content with wrong predecessor/operation/identity;
- post-terminal pair/ancestor/DACL/lock replacement, stale still-open handle and
  separate-reader mixed snapshot;
- File Bridge public owner loader result without Task-070 opened readback.

Expected: terminal exact zero or one; private readback exact zero or one; no
unbound pair authority; unrelated overwrite/delete zero. A terminal published
before a detected post-terminal drift is preserved but remains consumer effect
zero.

### T70-SUCCESSOR

- concurrent first provision with different operation/build against one genesis
  slot;
- two adoption terminals for the same predecessor pair;
- two upgrade builds/revisions from one predecessor, skipped revision and stale
  predecessor after a winning successor;
- two portable destinations from one predecessor and cross-lane reservation;
- reservation same coordinate with identical/different body, existing
  reservation without terminal and crash before/after PREPARED;
- operation/ticket/build-dependent reservation coordinate forgery;
- `VERIFY_REPAIR` observation promoted to a lineage successor.

Expected: one reservation and at most one exact successor per closed
single-successor lane; collision/recovery never creates PREPARED/target/consumer
effect; reservation/terminal/files are preserved; mutable head/latest scan zero.

### T70-JSON

- top/nested duplicate instance/path/hash/root/profile keys, equal/different;
- NaN/Infinity, BOM, trailing data, invalid UTF-8/control;
- deep/wide/huge strings, maps, lists and non-built-in values;
- caller-preparsed Mapping, unknown fields and noncanonical writer bytes.

Expected: pair/revision/terminal zero; ambiguous input preserved.

### T70-DURABILITY

- temp write/readback, file fsync, no-replace, directory durability and terminal
  readback failures;
- crash after PREPARED, descriptor, owner, pair readback and terminal namespace
  effect;
- foreign temporary replacement and cleanup failure.

Expected: no false PASS/DUPLICATE; own temp cleanup only through TASK-068 exact
handle identity; foreign/partial/published artifacts preserved.

### T70-LIFECYCLE

- repair tries to rewrite stable descriptor/owner;
- upgrade changes pair instead of immutable revision;
- missing/stale/forked revision predecessor or missing/wrong successor fence;
- copied/moved portable root, same bytes/different IDs, multiple predecessors;
- multiple adoption or portable successors from one predecessor;
- two installs share instance or terminal without explicit rebind lineage;
- uninstall/rollback deletes Bridge data, pair, revision or authority records;
- fixed ProgramData fallback or legacy automatic migration.

Expected: exact instance isolation; stable pair byte/identity retention; revision
or rebind terminal exact zero/one; learning data and legacy source preserved.

## 16. Acceptance criteria

Design acceptance requires:

1. Owner, one responsibility, exact Allowed Files and prohibited files are
   fixed.
2. The artifact/phase graph is acyclic and does not wait for unrelated Task
   completion before fixture work.
3. Caller/public values create no root, baseline, lease, plan or pair authority.
4. Production pair effects require exact TASK-063 plan, TASK-072 live ticket,
   TASK-068 immutable I/O and one pinned secure lease.
5. Descriptor and owner are read from simultaneously held exact opened
   snapshots; `PAIR_TERMINAL_V2` is durable audit state, and current consumer
   authority exists only through the post-terminal private one-use
   `INSTALLATION_PAIR_READBACK_V2`.
6. First publication is no-replace; repair/upgrade never replace the stable
   compatibility pair.
7. Every lineage-producing action acquires its immutable operation-independent
   single-successor reservation before PREPARED. Upgrade, adoption and portable
   rebind use the closed lane policy with no scan/current/latest inference.
8. The lease, pinned ancestors and both pair handles remain live through
   terminal readback; one final currentness attestation precedes private handoff
   and no publication follows that attestation.
9. Strict JSON, physical identity, DACL and ancestor currentness are verified at
   every effect seam.
10. File/directory durability failure is FAIL/completion-unknown, never PASS.
11. Automatic rollback/delete/repair of unknown or published state is zero.
12. Same committed event alone may be `DUPLICATE`; equality/collision is STOP.
13. Public output is body/path/OS-detail free and retains disabled/unauthorized
    defaults.
14. Fixture/static PASS is never promoted to installed/native/E2E/Production
    PASS.
15. Focused, negative, fault, package-contract and Windows-native tests pass
    with unrelated overwrite/delete zero.
16. Independent Critic returns `Critical=0 / High=0` and Judge returns `PASS`.

## 17. Verification plan

### Static/focused

- strict schemas and source/schema-resource exact mirrors;
- closed action/phase/transition maps;
- fixture schema and consumer contract tests;
- compileall and focused TASK-070 tests;
- TASK-068 fixture binding and TASK-063/TASK-072 contract regressions;
- diff/scope, public-error leakage and secret scan.

### Windows native

- root/data/authority/bridge handle and DACL attestation;
- lock existing/initial race, hardlink/reparse and handle replacement;
- concurrent two-process first provision exact zero/one;
- operation-independent successor reservation races for genesis, adoption,
  revision and portable rebind lanes;
- absent-to-appears and same-bytes/different-file-ID target races;
- descriptor/owner stat-open/read-post, terminal-window and post-terminal
  pair/ancestor/DACL/lock swaps;
- file/directory durability and readback fault injection;
- crash at every phase boundary with safe preservation;
- repair/upgrade/rebind/multiple-install isolation;
- packaged installer integration remains `NOT_EXECUTED` until TASK-063 owns its
  separate native Gate.

### Package/install contract

- TASK-063 creates only the exact pre-attested directories;
- Product uses the internally fixed TASK-068/TASK-072/TASK-070 composition;
- no Codex, ChatGPT, OpenAI key, internet or paid Provider dependency;
- distribution connector config remains byte-identical disabled;
- uninstall preserves Bridge data and authority artifacts by default;
- Release, real install and Production Activation remain separate Human Gates.

## 18. Independent completion receipt

The independent Critic/Judge reviewed technical-content SHA-256
`1fe4036d816317a3ca86265fd1155b209d7c33dac558b6880e4b511c5fe2810d`
(789 lines before this metadata-only status/receipt finalization) in full and
returned `Critical=0 / High=0` and `PASS / TECHNICAL DESIGN FROZEN`.

```text
task: TASK-070
design_identity: TASK070-PTD-INSTALLER-AUTHORITY-PAIR-V1
base: origin/main@35cdf1ad475633dcf035e0616e979b5a8fde0c88
allowed_files: docs/ai-team/tasks/TASK-070/complete-design-packet.md
reviewed_content_sha256: 1fe4036d816317a3ca86265fd1155b209d7c33dac558b6880e4b511c5fe2810d
critic: C0/H0
judge: PASS
source_effect: 0
schema_effect: 0
test_effect: 0
native_effect: 0
release_deploy_production_effect: 0
authority_created: false
next: fixture/source work in a fresh compliant worktree after dependency and overlap gates
```

This receipt freezes the technical design only. It creates no implementation,
install, Human, Release, Deploy or Production authority.
