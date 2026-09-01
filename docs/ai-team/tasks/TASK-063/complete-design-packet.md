# TASK-063 Installer Semantics and Installed Readback Corrective Design

Status: `DESIGN_COMPLETE / DEV-4 / SOURCE_START0 / NATIVE_NOT_EXECUTED`

Design identity: `TASK063-PTD-INSTALLER-SEMANTICS-READBACK-V2-R3`

Base: `origin/main@c27c24d6cb5f936e0549b743084bb9a9eaceb545`

## 0. Immutable review history

R1 technical snapshot is historical and is not a PASS artifact:

- SHA-256:
  `F91C8E5F598CBD63040093E7AFFE5EA1984C7563826AE8B20BEB16ABD3ECB44C`;
- independent Critic: Critical `0`, High `4`;
- Judge: `FAIL`;
- findings: pair-generation proof, same-operation TASK-072 binding
  currentness, exact-owned cleanup/crash proof and Windows Production-linkage
  hard gate were insufficient.

R2 technical snapshot is also historical and is not a PASS artifact:

- SHA-256:
  `C9CC5EFCE71FFF12D5677484DE2F6F6DF459AEB1B2348F9921E2D8B0BA012D35`;
- independent Critic: Critical `0`, High `1`;
- Judge: `FAIL`;
- finding: section 16.1 described the TASK-072 terminal consumer result before
  the installed-profile binding, contrary to the same-live-operation ordering
  required by sections 12 and 13.

R3 preserves the R1 and R2 snapshots and corrects only that terminal ordering.
The sole valid success sequence is live binding creation and verification,
then TASK-072 terminal-success record and pinned readback, then handle/lease
release. Source/schema/test/native authority remains zero until R3 receives a
fresh independent verdict.

## 1. Decision and historical boundary

TASK-063 continues to own installer-selected-root semantics, installation
instance lifecycle, package/revision meaning, and installed readback. It does
not reopen or negate the historical TASK-063 custom-path installer evidence.
That evidence remains valid for the exact source and host that produced it,
but it is not Production-linkage authority because the descriptor, owner,
readback and rollback paths were not one pinned physical transaction.

This corrective design replaces only the future authority boundary. A public
descriptor, owner document, discovery dataclass, path, hash, timestamp or
historical installer receipt is audit evidence. None can authorize creation,
repair, upgrade, portable rebind, rollback, downstream Profile work or
activation.

TASK-063 is the semantic orchestrator. It does not become a second secure I/O
foundation, owner-pair publisher, operation-ticket broker, File Bridge owner,
Human authorization broker or activation service.

## 2. Responsibility

TASK-063 owns:

- the exact installer-selected Product root and relative Bridge coordinate;
- the closed install action and lifecycle plan;
- package, payload-tree, Product build and installer-build meaning;
- creation/attestation of only the directory chain allocated to installation;
- the stable installation instance and predecessor/revision semantics;
- the descriptor semantic body supplied to TASK-070;
- consumption of TASK-070's private pair readback;
- semantic installed-instance verification and private
  `INSTALLATION_READBACK_V2` issuance;
- public body-free installed audit projection;
- repair, upgrade, portable-rebind and uninstall-preservation contracts;
- fixture ABI and focused/native acceptance for those responsibilities.

TASK-063 does not own:

- generic path, JSON, lock, temporary, no-replace or durability primitives
  (TASK-068);
- descriptor/owner pair lease, successor reservation, publication, pair
  terminal or physical pair readback (TASK-070);
- one-shot ticket, operation config, child launch or terminal broker event
  (TASK-072);
- File Bridge runtime layout, learning import, privacy, receipt/correlation or
  Profile publication (TASK-058/TASK-069);
- Preference promotion or DPAPI source authority (TASK-060);
- legacy migration, Profile binding or activation (TASK-061);
- canonical admission/currentness (TASK-067);
- Human authorization (TASK-071);
- release, deploy, Production Activation, destructive uninstall or data GC.

## 3. One-way artifact dependency graph

```text
TASK-068 IMMUTABLE_SECURE_IO_V1
TASK-072-A OP_TICKET_CORE_V1
TASK-063-A PRETERMINAL_SELECTED_INSTALL_PLAN_ABI_V1
    -> TASK-070 pair effect

TASK-070 PAIR_TERMINAL_V2
+ private TASK-070 INSTALLATION_PAIR_READBACK_V2
+ same live TASK-072 installer operation
    -> TASK-063-B INSTALLATION_READBACK_V2

TASK-063-B INSTALLATION_READBACK_V2
+ TASK-070 PAIR_TERMINAL_V2
    -> TASK-072-B INSTALLED_INSTANCE_PROFILE_BINDING_V1

TASK-072-B INSTALLED_INSTANCE_PROFILE_BINDING_V1
    -> TASK-060 / TASK-061-A / TASK-069 / TASK-036 / TASK-065
```

`PRETERMINAL_SELECTED_INSTALL_PLAN_ABI_V1` intentionally requires no TASK-070
terminal. `INSTALLATION_READBACK_V2` intentionally requires the TASK-070
terminal. TASK-072-A can issue a ticket before installation, while TASK-072-B
can bind an installed instance only after TASK-063 final readback. Therefore
no Task-level cycle exists.

TASK-070's public terminal is audit-only. TASK-063 receives the private
one-use pair readback while TASK-070 still holds its lease, ancestor snapshots
and both target handles. TASK-063 performs semantic finalization in that same
live call; it does not close and reopen the descriptor or owner by path.

The pair readback is one generation, not two individually valid documents.
Its indivisible generation coordinate is:

- one TASK-070 lease and successor reservation;
- one pair event/terminal and exact predecessor;
- one pinned common parent/ancestor security snapshot;
- descriptor and owner opened-handle file IDs, raw bytes and canonical hashes;
- simultaneous post-read handle/namespace/security currentness;
- one operation, ticket, install instance and expected pair-body commitment.

If either handle, target name, parent, DACL, pair event or reservation changes
before TASK-063 completes semantic validation, neither document is accepted
and no installed readback is issued. Equal fields or equal bytes from a
different file identity/generation never establish a pair.

## 4. Authority and effect ceilings

This Design Packet authorizes only task-local design mutation, review, commit,
push and one Draft design PR. Source/schema/test/native work remains
`SOURCE_START0` until this packet has independent Critical/High `0/0`, Judge
PASS, fresh overlap/lock checks and the required producer receipts.

Early fixture contracts may be issued with:

- `fixture_only=true`;
- `authority_created=false`;
- `native_effect_executed=false`;
- fixed fake identities and opaque commitments;
- no real install, directory, owner, descriptor, ticket or downstream effect.

Release, Deploy, Production Activation, paid Provider, private-media upload,
external-account mutation, destructive cleanup and real install are separate
Human Gates and remain zero.

## 5. Allowed Files

### 5.1 This design PR

- `docs/ai-team/tasks/TASK-063/complete-design-packet.md`

### 5.2 Future corrective implementation Atomic Units

- `src/ai_video_production/montage_learning_installation.py`
- `tests/test_task063_install_relative_bridge.py`
- `tests/test_task063_main_installer_contract.py`
- `schemas/montage-learning-installation-readback.schema.json`
- `src/ai_video_production/schema_resources/montage-learning-installation-readback.schema.json`
- `tests/fixtures/task063/**`
- `docs/ai-team/tasks/TASK-063/**`

The root and packaged schema are an inseparable byte-identical pair. A future
implementation unit may omit both; it may never edit only one.

## 6. Prohibited Files and effects

- `src/ai_video_production/secure_authority_io.py` and TASK-068 tests/docs;
- TASK-070/TASK-071/TASK-072 source, schemas, tests or docs;
- `src/ai_video_production/atomic.py`;
- `montage_learning_file_bridge.py`, bridge application, contracts, readiness
  and canonical-admission modules;
- TASK-060/TASK-061/TASK-065/TASK-067 source or schemas;
- installer CLI, packaged entry, Inno Setup, build scripts and package config;
- shared current-state, task index, roadmap, registry and CHANGELOG;
- existing unknown worktrees, branches, artifacts or installed directories;
- real install, repair, upgrade, portable move, uninstall, release, deploy,
  activation, legacy migration, provider, model download or native GUI effect.

Changing a prohibited consumer is a separate owner amendment. A fixture or
test seam may not be used to bypass that allocation.

## 7. Production composition and threat boundary

Production internally fixes:

- TASK-068 implementation/version and native Windows security backend;
- TASK-070 pair service/version;
- TASK-072 broker/action-profile/version;
- trusted clock, boot/session and installer process identity;
- Product, package, installer and payload-tree build digests;
- install security policy and descriptor contract version.

No argv, environment, current directory, registry fallback, config mapping,
serialized receipt, public dataclass, Python sentinel, monkeypatch, hook,
failure injector or caller-selected backend may choose those implementations.
Test composition is structurally separate and never packaged as a Production
entry surface.

The v2 threat model includes an uncooperative same-user namespace writer that
can race or replace ancestors, directories, locks, descriptor, owner, legacy
readback, temporary files and phase artifacts with symlink, junction/reparse,
hardlink, same-byte/different-file-ID or DACL variants. It includes concurrent
installer processes, repair/upgrade overlap, crash/restart, copied public
objects and caller-controlled JSON/time/action fields.

The design does not claim resistance to administrator compromise or arbitrary
memory injection into the trusted Product/broker process. That stronger
boundary requires a separately approved OS service/process-hardening Task.

## 8. Closed installation actions

The action is fixed by Product installer code, never caller text:

| Action | Meaning | Pair effect |
|---|---|---|
| `FIRST_PROVISION` | New selected root, new stable instance | TASK-070 `PAIR_GENESIS` |
| `ADOPT_EXISTING` | Exact trusted predecessor pair already exists | TASK-070 `PAIR_ADOPTION` |
| `VERIFY_REPAIR` | Read-only verification of current pair/package binding | no pair successor |
| `PUBLISH_INSTALL_REVISION` | Same immutable pair, new package/build revision | TASK-070 `REVISION` |
| `PORTABLE_REBIND` | Explicit new pre-created destination bound to predecessor | TASK-070 `REBIND` |

`UNINSTALL_PRESERVE` is a static/package lifecycle assertion, not a filesystem
operation in this Task. There is no action for delete data, merge instances,
automatic legacy import, fixed ProgramData fallback or automatic repair.

The action/result matrix is closed. Wrong action, cross-action ticket, unknown
action or a public string fails before directory, plan, ticket or pair effect.

## 9. Selected root and directory plan

The trusted installer supplies an already-opened selected-root handle and its
package/build context to private TASK-063 composition. TASK-063 derives only:

```text
<selected-root>\data
<selected-root>\data\montage-learning-bridge
<selected-root>\data\montage-learning-bridge\.immutable-authority
<selected-root>\data\montage-learning-bridge\learning-inbox
<selected-root>\data\montage-learning-bridge\learning-processing
<selected-root>\data\montage-learning-bridge\learning-quarantine
<selected-root>\data\montage-learning-bridge\learning-receipts
<selected-root>\data\montage-learning-bridge\preference
<selected-root>\data\montage-learning-bridge\preference\profiles
<selected-root>\data\montage-learning-bridge\state
<selected-root>\data\montage-learning-bridge\migration
```

Every component is a literal contained child; no caller path segment,
environment expansion, drive fallback, junction traversal or case-insensitive
alias is accepted. The fixed Bridge relative coordinate remains exactly
`data/montage-learning-bridge`.

On first provision, TASK-063 creates only absent exact components using native
create-new semantics and immediately pins handle identity, regular directory
type, no-reparse state, owner/DACL and parent identity. A race loser does not
retry. An existing component is allowed only under a predecessor-bound action
whose live attestation proves it belongs to the exact same instance and
operation plan. Safe-looking empty directories without that proof are not
adopted automatically.

TASK-063 holds the selected-root and created/existing directory handles through
TASK-070 pair terminal readback and TASK-063 final semantic handoff. DACL,
ancestor, case alias or namespace drift is STOP+preserve.

Directory creation is not delegated to `Path.mkdir(parents=True)`. Failure to
prove directory/namespace durability is FAIL or `COMPLETION_UNKNOWN`; it is
never PASS. TASK-068's inability to create directory trees is not silently
filled by treating a public path as authority.

## 10. `PRETERMINAL_SELECTED_INSTALL_PLAN_ABI_V1`

This is a private, nonserializable, noncopyable, one-use Product object. It is
issued only after root/directory/package attestation and before TASK-070 pair
effect. It binds:

- schema/contract version and closed action;
- one broker-authored operation ID and ticket event;
- selected-root live handle identity and security commitment;
- exact relative Bridge coordinate and all directory handle commitments;
- stable install instance or trusted predecessor instance;
- expected pair action, revision and predecessor terminal/reservation;
- descriptor semantic body commitment;
- expected TASK-058 owner semantic body commitment;
- package manifest, payload-tree, Product, installer and backend build digests;
- trusted creation/observation time domain;
- lifecycle flags: disabled, activation unauthorized, preserve data;
- expected TASK-068/TASK-070/TASK-072 implementation identities;
- consumer operation key and self commitment.

The public fixture projection contains only safe opaque commitments and fixed
false authority flags. It cannot be upgraded to a live plan by parsing,
copying, hashing, subclassing, pickling or importing a module token.

TASK-070 consumes the plan once. Entry marks the plan `IN_FLIGHT`; success,
failure or exception burns it. Restart requires fresh authoritative root,
package, predecessor and broker reconciliation. A public plan never resumes an
effect.

## 11. Descriptor semantics

TASK-063 owns the semantic descriptor body supplied to TASK-070. The stable
compatibility descriptor fields are closed:

- `schema_version`;
- `message_type`;
- `product_id`;
- `install_instance_id`;
- `bridge_relative_path`;
- `initial_installer_manifest_sha256`;
- `initial_product_build_sha256`;
- `created_at_utc`;
- `descriptor_sha256`.

The stable descriptor does not change on repair or upgrade. Current installer
manifest/build is recorded in TASK-070 `INSTALLATION_REVISION_V1`, not by
replacing the descriptor. `updated_at` is therefore removed from authority
semantics; any legacy mutable descriptor value remains audit-only.

TASK-058 owns the owner document semantics. TASK-063 may supply the expected
instance and fixed contract/profile commitments required by TASK-070 but may
not mint, parse-by-path, repair or replace owner authority.

Both fixed compatibility files are published/read together only by TASK-070.
TASK-063 never uses `AtomicJsonWriter` or direct path writes as authority.

## 12. Pair-readback consumption

After TASK-070 performs terminal pinned readback and its final no-publication
currentness check, it invokes TASK-063 with private one-use
`INSTALLATION_PAIR_READBACK_V2` while the lease, ancestors and both target
handles remain live.

TASK-063 validates in that call:

- exact descriptor semantics from the opened descriptor bytes;
- owner instance/contract/profile equality from the opened owner bytes;
- plan/action/operation/ticket equality;
- pair/revision/predecessor/successor reservation equality;
- selected root and Bridge relative coordinate;
- package/payload/build/backend/session equality;
- disabled/unauthorized lifecycle constants;
- TASK-070 terminal identity and final currentness result.

It additionally validates that descriptor and owner carry the same exact
TASK-070 pair generation and were simultaneously current after both reads.
Sequential path-valid documents, mixed terminal generations, pair-event
forks, or a swap between descriptor and owner validation are collision even
when every semantic field is equal.

It does not reopen either target, compare only hashes, call
`discover_installed_bridge(path)`, or accept a public TASK-070 receipt. The
private pair readback is consumed once and burned on success or exception.

## 13. `INSTALLATION_READBACK_V2`

`INSTALLATION_READBACK_V2` is a private one-use semantic object issued in the
same live call after section 12 succeeds. It binds:

- exact Task identity/version/action;
- install instance and selected-root security commitment;
- descriptor/owner canonical hashes and pair terminal;
- installation revision and predecessor;
- package, payload-tree, Product and installer build commitments;
- Task-068/070/072 implementation and broker event commitments;
- trusted clock/boot/session and currentness window;
- exact directory-set commitment;
- `connector_enabled=false`;
- `activation_authorized=false`;
- `automatic_learning_promotion_authorized=false`;
- `native_install_observed` separately from design/static evidence;
- public audit projection hash.

The object is nonserializable, noncopyable, non-subclassable and bound to the
exact downstream consumer operation. Entry changes it to `IN_FLIGHT`; success
or exception burns it. A later consumer requires a fresh TASK-070
consumer-supplied terminal reread under a fresh trusted operation.

TASK-063 emits no additional filesystem publication after TASK-070's final
pair currentness check. While the source handles and pair lease remain live,
TASK-072 first uses the private object to create and verify
`INSTALLED_INSTANCE_PROFILE_BINDING_V1`. Only after that binding succeeds may
TASK-072 record its terminal-success event and complete a pinned exact
readback. The handles and lease are released only after that readback. This is
the sole success ordering; a binding failure, terminal publish/readback
failure or crash at any earlier seam records terminal success zero. It also
preserves TASK-070's rule that TASK-063 makes no durable publication after the
final pair check.

That TASK-072 transition is part of the same live operation, not a later
path-based composition. Before recording its terminal event, TASK-072 and
TASK-063 jointly revalidate:

- broker operation/ticket identity and unexpired current session;
- selected install instance and exact TASK-070 pair generation;
- selected-root and writable data-root opened ancestor/security commitments;
- expected Owner SID/session/scope commitment;
- installation revision, package/payload/build and disabled constants;
- consumer identity and expected profile-binding body.

The private installed readback is consumed directly into the Task-072 binding
while the source handles/lease remain live. Wrong owner, data root, instance,
revision, operation, backend or phase produces no binding and no terminal
success. A public receipt, hash equality or later reopen cannot repair it.

## 14. Public audit projection and schema

The public `BvpInstallationReadbackAuditV2` projection is data only. Its exact
fields are:

- `schema_version` = `2.0.0`;
- `message_type` = `BvpInstallationReadbackAudit`;
- `task_id` = `TASK-063`;
- `action`;
- `operation_commitment_sha256`;
- `install_instance_commitment_sha256`;
- `pair_terminal_sha256`;
- `installation_revision`;
- `descriptor_sha256`;
- `owner_manifest_sha256`;
- `package_manifest_sha256`;
- `payload_tree_sha256`;
- `product_build_sha256`;
- `installer_build_sha256`;
- `directory_set_sha256`;
- `observed_at_utc`;
- `status` = `VERIFIED_DISABLED` or `BLOCKED`;
- `reason_codes` as a bounded sorted closed enum list;
- `connector_enabled` = `false`;
- `activation_authorized` = `false`;
- `native_install_observed`;
- `fixture_only`;
- `authority_created` = `false`;
- `currentness_selected` = `false`;
- `audit_self_hash`.

No absolute/relative filesystem path, username, SID, DACL, file ID, raw body,
argv, OS error, package path or private handle appears publicly. The install
instance is an opaque commitment, not the raw identifier. The public status
does not create installer or downstream authority.

The root/package schema mirrors use Draft 2020-12, `additionalProperties=false`,
closed enums, exact built-in scalar types and bounded strings/arrays. The hash
domain excludes only `audit_self_hash` and uses canonical JSON bytes.

## 15. Strict JSON and physical snapshots

All authority JSON is parsed by TASK-068/TASK-070 from the same opened bounded
snapshot before semantic validation or hashing. Reject:

- duplicate keys at every depth, equal or different;
- NaN, Infinity and negative Infinity;
- BOM, trailing non-whitespace, invalid UTF-8 and disallowed controls;
- non-built-in mappings/scalars or cyclic values;
- oversized bytes, strings, depth, nodes, members or items;
- missing, extra, wrong-type or noncanonical fields.

Raw bytes hash, canonical parsed hash, physical identity, ancestor/security
commitment and opened handle remain one private snapshot. Ambiguous legacy
descriptor, owner, fixed installer readback or rollback preimage is preserved;
it is never normalized, repaired, rewritten or deleted.

## 16. Lifecycle state machine

### 16.1 First provision

1. Pin the existing selected Product root and package/build evidence.
2. Acquire TASK-072 `INSTALL_AUTHORITY_PAIR_WRITE` authorization.
3. Create/attest the exact directory plan without recursive fallback.
4. Issue the private TASK-063 preterminal plan.
5. TASK-070 acquires its pair lease and successor reservation.
6. TASK-070 publishes/reads the immutable pair event chain and fixed pair.
7. TASK-063 consumes the live pair readback and issues private installed
   readback.
8. With the source handles and pair lease still live, TASK-072 creates and
   verifies `INSTALLED_INSTANCE_PROFILE_BINDING_V1`.
9. TASK-072 records terminal success and completes its pinned exact readback.
10. Only then are the source handles and pair lease released.

A failure or crash during steps 7 through 9 leaves terminal success absent.
Recovery cannot infer or backfill success from a public receipt, equal fields,
or a later reopen; it requires a fresh authoritative operation and reread.

Concurrent first provision has one reservation winner. The loser returns a
stable body-free collision/recovery code with effect zero and no automatic
retry.

### 16.2 Verify/repair

Repair does not replace descriptor or owner. It performs a fresh authoritative
pair readback and verifies package/directory state. Missing/mismatched Product
payload is installer/package recovery evidence, not permission to rewrite the
pair. Unknown one-sided state is STOP+preserve.

### 16.3 Upgrade

Upgrade validates the exact predecessor pair/readback and new package tree,
then asks TASK-070 for one `INSTALLATION_REVISION_V1`. Pair bytes/identity and
instance remain unchanged. Revision gap, fork, same revision/different build,
stale predecessor or concurrent successor is STOP.

### 16.4 Adopt existing

Adoption requires an exact predecessor installed readback and simultaneous
pair handle verification. Content equality, raw instance ID, copied install,
directory scan or legacy fixed receipt is insufficient. It publishes only the
TASK-070 adoption chain; it does not rewrite compatibility files.

### 16.5 Portable rebind

Portable rebind is explicit and destination-specific. The destination must be
pre-created, pinned and empty under a fresh trusted plan. TASK-070 consumes the
predecessor's single `REBIND` reservation. No directory copy/move, automatic
source revocation or old-data deletion occurs. A manually copied tree is STOP.

### 16.6 Uninstall

TASK-063 performs no uninstall deletion. Static installer-contract tests must
prove Bridge data, pair/history, learning data and legacy source are absent
from recursive uninstall deletion. Physical GC requires a separate Task and
Human Gate.

## 17. Legacy compatibility disposition

Existing public functions and fixed artifacts have these dispositions:

| Surface | Production v2 disposition |
|---|---|
| `provision_installed_bridge` | legacy/test audit wrapper; no Product effect without private composition |
| `discover_installed_bridge` | legacy audit only; path result never authority |
| `provision_and_write_installer_readback` | legacy/test wrapper; Production fixed readback mutation unavailable |
| `write_installer_readback` | legacy/test wrapper; public path write cannot satisfy v2 |
| `bridge-instance.json` | stable TASK-070 compatibility descriptor |
| `bridge-owner.json` | stable TASK-070 compatibility owner pair |
| `migration/installer-readback.json` | historical audit input, never currentness/authority |
| `AtomicJsonWriter` / `exclusive_file_update_lock` | not authority proof and unavailable to Production v2 |

The Production packaged entry is outside this correction's Allowed Files and
therefore remains fail-closed until its owner consumes the exact private
composition. TASK-063 cannot claim real packaged linkage from source-only or
fixture tests.

## 18. Failure and recovery rules

- Before any namespace effect: stable failure, confirmed effect zero.
- After owned namespace publication but before durable/current readback:
  `COMPLETION_UNKNOWN`, preserve all state, no retry or rollback.
- A committed exact terminal may be recognized only by the same reservation,
  operation body, pair identities and authoritative reread.
- Same committed event may return `DUPLICATE`; same bytes, same raw instance,
  different inode, different body or different operation is collision.
- Unknown one-sided state is not repaired automatically.
- Operation-owned temporary cleanup is TASK-068/TASK-070 responsibility and
  only for the exact live identity. TASK-063 deletes nothing.
- TASK-063 may request no rollback or cleanup by path. TASK-068/TASK-070 may
  unlink only an exact current-operation-created namespace entry whose live
  handle/file ID, parent identity and creation journal all still match. A
  closed-handle path, equal bytes, deterministic temp name or previous
  operation record is insufficient.
- If a descriptor, owner, temp, directory or revision target is replaced,
  linked, reparsed or becomes identity-ambiguous at any crash/failure seam,
  cleanup/restore/delete is exactly zero and state is preserved for Human or
  owner recovery.
- Restart never recovers from public objects, fixed readback, highest/latest
  scan, timestamp, filename or caller-selected predecessor.
- A burned ticket, plan, pair readback or installed readback is never reused.
- Public errors/logs/stdout expose stable code and opaque commitments only.

## 19. Privacy and logging

TASK-063 processes metadata, not media. Even so, install paths, account names,
SIDs, emails, hostnames, argv and OS error strings are sensitive and remain
private. Public reason codes are closed enums. Free-form exception text is not
serialized into receipts or logs.

No receipt, fixture promoted as real, log, stdout or error may contain:

- absolute drive/UNC/home/repository/install paths;
- usernames, SIDs, account/email identifiers;
- secrets, tokens or environment values;
- descriptor/owner bodies;
- OS error text or native handle/file IDs.

## 20. Negative and fault matrix

### I63-PATH

- relative/rooted/UNC/device/alternate-data-stream/case-alias coordinates;
- selected-root/data/bridge/authority ancestor swap;
- symlink, junction/reparse, hardlink and DACL drift;
- fixed ProgramData fallback or caller environment root.

Expected: plan/ticket/pair/receipt effect zero; no external path delta.

### I63-READ

- descriptor and owner stat-open/read-post swap;
- same bytes/different inode;
- descriptor/owner mixed generation;
- descriptor terminal generation N plus owner terminal generation N-1/N+1;
- descriptor validated then owner/parent/pair-event swapped before the joint
  post-read currentness barrier;
- duplicate keys equal/different at top/nested fields;
- NaN/Infinity, BOM, trailing data, invalid UTF-8/control, deep/wide/huge;
- public dataclass/hash/copy/pickle/subclass/duck-type forgery.

Expected: private installed readback zero; public status `BLOCKED`; files
preserved.

### I63-LOCK/PAIR

- concurrent first provision and reservation race;
- existing/initial lock hardlink/reparse/DACL/ancestor drift;
- descriptor absent then appears identical/different;
- owner appears before descriptor and descriptor before owner;
- pair post-terminal/final-check swap;
- same semantic bodies under different file IDs or different pair generation;
- wrong TASK-068/070/072 backend or phase switch.

Expected: pair exact zero/one, no false duplicate, unrelated overwrite/delete
zero.

### I63-TICKET/CAPABILITY

- direct/copy/serialized preterminal plan;
- public TASK-070 terminal without private pair readback;
- wrong action/instance/root/package/build/predecessor/revision;
- expired/replayed/cross-operation/cross-session ticket;
- double/concurrent/exception reuse;
- caller clock, backend, hook or failure injector in Production.
- broker terminal/profile binding after lease release or later path reopen;
- wrong selected Owner SID/session, writable data-root identity or pair
  generation between TASK-063 readback and TASK-072 terminal recording.

Expected: directory/pair/readback/downstream effect zero.

### I63-DURABILITY/CRASH

- failure before/after each directory create and DACL check;
- file fsync, namespace commit, directory durability or pair readback failure;
- crash after PREPARED, descriptor, owner, pair terminal and final check;
- Task-072 terminal publication failure after exact pair completion;
- restart with same/different operation body.
- foreign replacement of current-operation temp/descriptor/owner/revision or
  created directory immediately before cleanup/rollback;
- cleanup candidate with equal bytes/name but different file ID, parent or
  creating operation.

Expected: no fabricated PASS; completion unknown is explicit; preserve all
published/foreign state; automatic retry/rollback/delete zero. Cleanup delta
is asserted separately for every crash seam and is zero unless TASK-068/070
proves the exact live current-operation-created identity.

### I63-BINDING

- TASK-072 broker operation/ticket, installed profile action or backend switch;
- wrong install instance, selected root, data root, Owner SID/session/scope;
- pair/revision/package/build/currentness changes before terminal recording;
- public installed audit or public TASK-070 terminal substituted for either
  private object;
- terminal recording delayed until after lease/handles are released.

Expected: Task-072 installed profile binding zero, terminal success zero,
TASK-063 installed readback burned, pair/Project/Profile/config unchanged.

### I63-LIFECYCLE

- repair foreign replacement or ambiguous preimage;
- upgrade fork/gap/stale predecessor/same revision different build;
- multiple installs with same raw instance or mixed pair;
- portable copied/nonempty/mixed destination;
- uninstall manifest attempts Bridge/data deletion;
- legacy source present, missing or replaced.

Expected: instance isolation, stable pair retention, exact revision/rebind
zero/one, learning and legacy data preserved.

### I63-PUBLIC

- public path/OS error/body/SID/account leakage;
- audit receipt relabelled as authority;
- fixture changed to `fixture_only=false`;
- `connector_enabled=true` or `activation_authorized=true` injection;
- unknown/extra public fields.

Expected: reject/body-free; activation/Profile/history mutation zero.

## 21. Acceptance criteria

1. Owner, responsibility, Allowed Files and prohibitions are exact.
2. The artifact graph is one-way and compatible with canonical TASK-070 and
   TASK-072 contracts.
3. Public path/hash/dataclass/receipt values create no installer authority.
4. Production effects require exact internally fixed TASK-068/070/072
   composition and live private objects.
5. The selected root and directory chain are handle/security pinned; no fixed
   fallback or recursive path authority exists.
6. Descriptor/owner are stable no-replace compatibility pair artifacts owned
   physically by TASK-070; repair/upgrade never replace them.
7. TASK-063 consumes both simultaneously opened snapshots through TASK-070 and
   performs no later path reopen as authority.
8. Private `INSTALLATION_READBACK_V2` is single-use and its public projection
   is body/path-free and non-authoritative.
9. TASK-063 performs no publication after TASK-070's final pair currentness
   check; TASK-072 owns terminal broker recording.
10. Descriptor and owner are one exact TASK-070 physical generation with a
   simultaneous post-read barrier; individually valid or equal documents from
   another identity/generation are rejected.
11. TASK-072 installed profile binding consumes the private installed readback
   in the same live operation and revalidates instance, Owner, data root,
   pair/revision, broker and backend before terminal success. The terminal
   event and pinned readback precede handle/lease release; binding failure,
   terminal failure or any earlier crash records terminal success zero.
12. Strict JSON, identity, ancestor, DACL, package and operation currentness are
    bound in one live operation.
13. First provision, adoption, repair, revision and rebind have closed,
    non-overlapping semantics.
14. Unknown/collision/one-sided state is STOP+preserve; rollback/delete/repair
    of foreign state is zero.
15. Cleanup is allowed only for an exact live current-operation-created
    identity proven by TASK-068/070; all foreign/ambiguous replacements have
    cleanup/restore/delete zero at every crash seam.
16. Directory/file durability uncertainty is never PASS.
17. Uninstall preserves Bridge, learning and authority data by default.
18. Distribution connector configuration stays byte-identical disabled;
    activation and Profile effects remain zero.
19. Focused, negative, fault, package-contract and Windows-native tests pass
    with unrelated overwrite/delete zero.
20. Fixture/static PASS is never promoted to installed/native/E2E/Production
    PASS.
21. Independent Critic returns Critical/High `0/0` and Judge returns PASS.

## 22. Verification plan

### Static/focused

- compile/schema validation and exact root/package schema mirror;
- closed field/action/reason-code tests;
- plan/pair/readback fixture compatibility with TASK-070/TASK-072;
- existing custom Unicode root and fixed ProgramData literal regressions;
- source symbol disposition and prohibited-import checks;
- public error/log leakage and secret scan;
- diff/scope check.

### Windows native

- real file IDs, reparse/junction/hardlink and DACL checks;
- existing/initial directory and concurrent first-provision races;
- descriptor/owner same-open snapshot and mixed-generation rejection;
- same bytes/different file ID and ancestor swaps;
- file/directory durability fault injection;
- crash/restart at every TASK-063/TASK-070/TASK-072 seam;
- repair, upgrade, adoption, portable rebind and multi-install isolation;
- real installer provision/repair/upgrade/readback only under a separately
  authorized bounded native Gate.

### Production-linkage hard gate

Source, fixture and cross-platform tests can close implementation units but
cannot make TASK-063 Production-linkage eligible. Eligibility additionally
requires one bounded Windows evidence run against the exact candidate build
and exact TASK-068/070/072 versions. The run must PASS all of:

- concurrent first provision and update with exactly one pair/revision winner;
- descriptor/owner simultaneously opened same-generation readback;
- same-bytes/different-file-ID and mixed-generation rejection;
- ancestor/reparse/hardlink/DACL swaps at every pre/post-read barrier;
- file fsync, pair namespace commit and every directory durability failure;
- swap immediately before/after pair publication and before TASK-072 binding;
- post-publish/final-readback mismatch and lease-release ordering;
- crash after each directory, reservation, descriptor, owner, revision,
  pair-terminal, semantic-readback and broker-terminal seam;
- foreign temp/target/directory replacement with overwrite/delete/restore zero;
- repair, upgrade, adoption, portable rebind, multi-install and uninstall
  preservation readback.

Every case records descriptor delta, owner delta, pair/revision delta,
Task-072 terminal/profile-binding delta, unrelated overwrite/delete delta and
legacy/learning preservation separately. Required invariants are pair/revision
effect exact `0/1`, terminal/profile binding exact `0/1`, unrelated overwrite/
delete `0`, foreign cleanup `0`, and no PASS when durability/currentness is
unknown. Windows tests skipped, unavailable or simulated remain
`NOT_EXECUTED / NOT_CONFIRMED`, so Production linkage remains N.C.

### Package/lifecycle

- selected destination and exact relative layout;
- package/payload-tree/build commitments;
- packaged entry uses private composition, never caller backend/path authority;
- connector config remains disabled;
- uninstall excludes Bridge/data/history;
- no ProgramData fallback, legacy copy/move or automatic activation.

Native operations that were not executed remain `NOT_EXECUTED`, not PASS.

## 23. Implementation Atomic Units after `DESIGN_COMPLETE`

1. `U1 ABI_FIXTURES`: private/public value contracts, schema pair, fixtures and
   pure forgery/strict-JSON tests; filesystem effect zero.
2. `U2 FAIL_CLOSED_SURFACE`: legacy public mutation surfaces stop before
   Product effects when private composition is absent; isolated tests remain
   bounded.
3. `U3 ROOT_PLAN`: trusted root/directory plan and fault-port tests; real
   TASK-068/072 binding parked.
4. `U4 PAIR_CONSUMER`: TASK-070 fixture/private pair readback semantic consumer
   and single-use installed readback; real pair binding parked.
5. `U5 LIFECYCLE`: repair/revision/adoption/rebind pure state and negative
   models; real installer effects zero.
6. `U6 REAL_BIND`: only after canonical TASK-068, implemented TASK-070 and
   TASK-072 receipts plus fresh overlap/lock; local bounded test effects only.
7. `U7 NATIVE_EVIDENCE`: separately authorized real installer provision,
   repair, upgrade and readback; Release/Deploy/Activation remain zero.

Every unit requires focused tests, relevant regression, independent DEV-4
review, diff/scope audit and explicit effect accounting before the next unit.

## 24. Design completion receipt

`TASK063-DESIGN-R3-ACCEPTED-2026-09-01`

- reviewed technical-content SHA-256:
  `8D1EFD1A7AA33BDBEE1236561A3D4B225AE9DFFE7409C3AC7B2272A7D6851B52`;
- reviewed size: `832` lines / `38925` bytes;
- before/after snapshot identity: exact match;
- independent Critic: Critical `0`, High `0`, Medium `0`, Low `0`;
- Judge: `PASS`;
- R2 sole High: closed by the R3 terminal-ordering correction;
- source/schema/test mutation authority: `START0` pending fresh
  origin/main, overlap, exact lock and producer completion receipts;
- required producers before real binding: TASK-068, TASK-070 and TASK-072;
- Windows Production-linkage: `NATIVE_NOT_EXECUTED / NOT_CONFIRMED` and a
  separate hard Gate;
- packaged entry, real install, Release, Deploy and Production Activation:
  effect `0`.

This receipt accepts only the exact R3 technical snapshot. The metadata-only
status and receipt finalization above do not alter its normative contracts.
Design completion creates no source, installer, native, release, deploy or
Production authority.
