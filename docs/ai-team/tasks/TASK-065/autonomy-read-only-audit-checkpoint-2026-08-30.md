# TASK-065 Autonomous Read-only Dependency Audit Checkpoint

Date: 2026-08-30
Task: TASK-065
Atomic Unit: PL-A preparation and dependency re-entry audit
Technical state: `DEPENDENCY_GATED / EFFECT0`

## 1. Exact audit bind

- TASK-065 worktree:
  `D:\BAI\BAI VIDEO PRODUCTION FOR DRFX\bai_video_production\.worktrees\task065-production-linkage-design`.
- Branch: `codex/task-065-production-linkage-design`.
- Documentation checkpoint parent: `eb9d8c57a6b373606df5e9f9e593779590a5e785`.
- Audited canonical remote `main`:
  `160c9569673fbf65a28b0f95eeb44c5b0111584f`.
- TASK-063 corrective PR #448 exact head:
  `ca8aa736ad56e07a54120eea6ee4bfeefb68454b`.
- The source/schema/test audit applies to its parent
  `0b95e40861a21100a21802035ed5fe1900d600df`; the sole child delta is one
  TASK-063 `CHANGELOG.md` bullet and does not change those audited blobs.
- TASK-060 PP-A PR #430 exact head:
  `b8707e61f4db9f7f9a6c5b42f93bcb61c02a8066`.

This checkpoint records read-only findings only. It performs no BVP source,
schema, test, shared document, installed SKILL config, native, Release, Deploy,
or Production mutation.

## 2. D0 exact-head audit — TASK-063 PR #448

### 2.1 Changes that close the originally reported defects

The exact PR head removes the arbitrary `--receipt-output` CLI option and
publishes only to the fixed installer-relative
`migration/installer-readback.json` coordinate. The writer validates the fixed
layout, rejects unsafe existing targets, writes a same-directory temporary,
flushes it, and uses link-create for an absent target or replace for an owned
existing target.

The Windows acceptance script now uses a separator-aware containment boundary
instead of raw sibling-prefix matching. The Inno Setup installer also captures
an existing-ancestor identity snapshot in `PrepareToInstall` and compares it at
`ssInstall` before payload placement.

Focused negative/fault coverage at the exact head includes:

- arbitrary receipt argument rejection;
- forged layout rejection;
- existing directory, symlink, and hardlink target rejection;
- migration ancestor swap rejection;
- replace failure preserving existing bytes;
- malformed existing receipt rejection;
- concurrent creation of a previously absent target;
- post-write corruption/read-back mismatch; and
- safe update with one final hardlink name.

At the final exact-head check, all Ubuntu jobs, Windows 3.12/3.13, release
metadata, dependency audit, and secret scan pass. Windows 3.11 fails one
existing TASK-058 multiprocess serialization regression: a generic worker
leaks raw `PermissionError` for an admission-journal access race instead of one
of the closed domain errors expected by the test. The run result is `1 failed,
4734 passed, 8 skipped`. This is outside the TASK-063 changed paths, but an
exact-head failure cannot be relabeled PASS. The PR is still a draft with no
reviews and `mergeStateStatus=UNSTABLE`; it is not a canonical D0 completion.

### 2.2 Residual D0 acceptance blockers

The following findings are independent TASK-065 consumer-side blockers. They do
not amend TASK-063 source and are not final severity decisions for its owner.

1. **Discovery-to-publication currentness is not revalidated.**
   `discover_installed_bridge` returns a descriptor and owner snapshot, while
   `write_installer_readback` publishes the cached values without reopening the
   descriptor and owner files. A valid instance update between those calls can
   therefore produce a stale but internally shaped receipt.
2. **Existing receipt ownership does not bind the descriptor digest.**
   `_validate_existing_installer_readback` compares every ownership coordinate
   except `descriptor_sha256`; that field is only syntax-checked. A shaped
   existing receipt with the same instance/owner but an unrelated valid SHA can
   be accepted for overwrite. Upgrade support needs an explicit prior/current
   descriptor transition rule rather than omission of the binding.
3. **The existing-target CAS has a final replacement gap.**
   The writer closes the inspected handle, performs its last identity/byte
   comparison, and then calls `os.replace`. A target substitution after the
   comparison and before replace is not pinned by handle or retried as a
   compare-and-swap. Current tests inject before the comparison, not inside
   this final gap.
4. **The new-target link cleanup failure has no recovery proof.**
   The absent-target path creates the public hardlink and then unlinks the
   temporary name. If unlink fails, publication has already occurred and may
   leave multiple names. No focused fault test establishes the required
   resulting state or cleanup boundary.
5. **Python receipt publication does not inspect ancestors above
   `install_root`.** `_installer_readback_coordinates` checks identities from
   the selected install root down to the migration directory. A stable reparse
   ancestor above the selected root is outside that tuple. The Inno Setup
   preflight partly covers this, but the private discovery command remains a
   separately callable boundary and must not treat a resolved path string as
   proof that no ancestor was traversed.
6. **There is no fresh ancestor recheck at `ssPostInstall`.**
   The installer compares its snapshot at `ssInstall`, then later executes the
   newly placed product at `ssPostInstall` to provision and discover. There is
   no second full-chain identity comparison immediately before those executions.
7. **The packaged acceptance read-back is incomplete.**
   The PowerShell test checks the relative path, instance equality, and disabled
   flags, but does not independently recompute and compare the descriptor
   self-hash and owner-manifest self-hash carried by the discovery receipt.
   Its post-install path evidence also lacks a final stable file-identity
   comparison for the complete ancestor chain.

D0 must remain fail-closed until the owning task resolves or explicitly closes
these boundaries, merges a corrective exact head to canonical `main`, passes
post-main checks, and supplies a fresh installed-instance read-back.

## 3. D1/D2 canonical source reachability audit

TASK-060 and TASK-061 both name accepted design commit
`0ac8971174ab227a6f62b8b797307bbc31b70145` with design digest
`sha256:c54623039fc8197c6bf8d02d5363ae53b601e4feef400243fa8be1f4b2280353`.
The preceding accepted identity recorded by the reservation amendment is
`9f6c26ac5147b9a881ca037ae02ef020818db50a`.

Both commit objects are absent from the canonical local object database and
GitHub's canonical commit endpoint returns `No commit found` for each SHA. An
exact-hash search of the canonical checkout and the known local BVP worktree
root finds only references in task/lock metadata; it does not find the accepted
design body. Thus the accepted design identity is recorded but its actual
contract is not independently reopenable.

This is a canonical re-entry failure, not permission to infer missing fields.
D1 and D2 require one of the following before implementation can count:

- a reachable canonical commit/blob that contains the exact accepted design
  body and verifies the recorded digest; or
- a new canonical rebind that embeds or points to the exact closed design body
  and supersedes the unreachable identities.

PR #430 is the only current TASK-060 implementation PR. It contains PP-A only,
is an open draft, remains `UNSTABLE`, and has no PP-B or PP-C source/schema/
receipt. Its candidate envelope is explicitly `READY_FOR_HUMAN_REVIEW` and is
not the promoted read-only production source required by TASK-065.

No TASK-061 implementation PR exists. TASK-061 remains
`DEPENDENCY_BLOCKED / IMPLEMENTATION_NOT_AUTHORIZED`. Its public-readiness-v2
wording still conflicts with the released TASK-058 boundary: public/package
readiness is v1, while `_ConnectorReadinessEvidenceV2` is private and
non-exported. CA-A, CA-B, and CA-C receipts remain absent.

## 4. Config CAS and lifecycle source audit

### 4.1 Current installed SKILL config cannot supply a revision by itself

The released ConnectorConfig v1 schema has exactly nine fields. It has no
config revision, body hash, self-hash, predecessor, or CAS coordinate. The
adapter's `load_connector_config` performs a normal JSON read, closed-field
validation, and absolute-path validation; it is not a config writer and does
not provide stable physical-file identity.

Therefore PL-B must not invent a revision from timestamps, path text, or file
length. Its future compare-and-swap input must combine:

1. the exact CA-C-defined config revision/body hash/history coordinate;
2. an independently captured current config byte hash and physical file
   identity;
3. the TASK-063 admitted installed-instance and derived Bridge coordinate; and
4. a pre-write and post-write owner/DACL/reparse/hardlink/ancestor attestation.

Duplicate same body may be a no-op only when all four coordinates remain
current. Same revision with a different body, missing revision authority, or
identity drift is `STOP / EFFECT0`.

### 4.2 Lifecycle matrix

| Case | Exact-head source evidence | TASK-065 admission consequence |
|---|---|---|
| custom install root | Unicode/space custom-root focused test and fixed relative layout | candidate only until D0 canonical/post-main read-back |
| same-root upgrade | Inno Setup uses previous app directory; provision preserves instance and created time while refreshing descriptor | require an explicit prior/current descriptor receipt chain |
| second installation | a new root can mint a different opaque instance UUID | never auto-select; more than one eligible instance is `MULTI_INSTALL_AMBIGUOUS` |
| stale old installation | there is no canonical global active-instance selector in TASK-063 | require external canonical currentness evidence; stale is disabled/effect0 |
| uninstall | dynamically provisioned Bridge paths are not listed for recursive installer deletion | require real uninstall preservation read-back; file-layout intent alone is not runtime PASS |
| existing receipt update | new-or-owned update path exists | blocked until descriptor binding and final CAS gap are closed |
| hardlink/reparse | existing receipt aliases/reparse are rejected and current fixture has one observed name | require complete ancestor and post-action identity proof |
| config DACL | current installed config inherits Modify for non-owner principals recorded in the PL-A freeze | ownership policy must resolve every writable or unknown principal before PL-B |

### 4.3 Fresh installed-config physical identity

The exact installed config was reopened after the dependency audit. It remains
406 bytes with SHA-256
`da41b71292fd2a9fa2070eba531e06fafc0e84f9bbc1d26c27b0af79c5e2db6c`,
owner `PC-BAIS\user`, ordinary `Archive` attributes, no link target, and one
reported hardlink name. The observed NTFS file ID is
`0x00000000000000000027000000167513`.

The complete inspected chain from `C:\` through the adapter `config` directory
reports no link target or reparse-point attribute. The file DACL is inherited
and still grants `Modify, Synchronize` to `PC-BAIS\CodexSandboxUsers` and the
unresolved principal
`S-1-5-21-3254314496-1160912775-205898531-2731828939`; SYSTEM,
Administrators, and the owner retain FullControl.

This point-in-time file ID and byte hash are useful PL-B CAS inputs, but are not
a CA-C revision or ownership attestation. The unresolved writable principals
keep the current classification `CONFIG_DACL_UNATTESTED / EFFECT0`.

### 4.4 Installed-config ACL provenance

The writable ACEs are not inherited from the user profile, `.codex`, or
`skills` directory. They are explicit inheritable ACEs introduced at the
`bvp-montage-learning-adapter` installed SKILL root and inherited by `config`
and the config file:

- `PC-BAIS\CodexSandboxUsers`: `Modify, Synchronize`;
- `S-1-5-21-3254314496-1160912775-205898531-2731828939`:
  `Modify, Synchronize`.

The second SID does not translate to an NT account, produces no
`Win32_Account` result, and is not present in the current process token groups.
It is therefore an unresolved/orphan candidate, not an implicitly trusted
writer. PL-B must bind an explicit allowed-writer policy and reject every
unlisted writable ACE. It must not assume that either all non-owner writers are
forbidden or that installation-time ACL presence makes a principal trusted.

### 4.5 Existing persistence primitives are not PL-B authority

The repository contains useful but insufficient precedent:

- `ConnectionSettingsStore` supplies a logical integer revision and
  document self-hash, but reads by path and publishes through the generic
  `AtomicJsonWriter`. Its record schema is unrelated to the closed installed
  ConnectorConfig v1 schema.
- `AtomicJsonWriter` creates parent directories and performs unconditional
  path-based `os.replace`; it does not pin the existing target, DACL, hardlink,
  or complete ancestor identity and cannot be used alone for PL-B.
- TASK-058's `_WindowsPinnedReadPort` demonstrates non-inheritable Win32
  handle reads and file IDs, but it is private, read-only, limited to its
  Project-root chain, and its public projection explicitly leaves hostile
  ancestor namespace-race protection false.

TASK-065 must not import these private helpers as authority or reuse the generic
writer unchanged. After D0-D2 and the separate config Gate, PL-B needs a
task-owned closed transaction that combines the CA-C logical revision/body
identity with a complete physical-path snapshot and exact post-write read-back,
while preserving every non-coordinate config field including `enabled`.

### 4.6 CA-C history and PL-B coordinate-successor contract

The current ConnectorConfig is a single closed JSON body. Changing only
`bridge_root` still changes its whole-file byte hash. If CA-C later binds its
Human activation/history receipt to exact config bytes, a PL-B coordinate
update would otherwise make the CA-C authority stale even though PL-B did not
touch `enabled`.

D2 is therefore not admissible unless the canonical CA-C contract defines one
of these equivalent closed outcomes:

- an exact pre-authorized coordinate-only successor body/revision that PL-B may
  publish by CAS while leaving Human activation entries immutable; or
- separate activation-field and linkage-coordinate identities plus an exact
  composition/read-back rule that still authenticates the final whole config.

PL-B may not invent that split. Its deterministic candidate delta must be
exactly `{bridge_root}`, with all eight other ConnectorConfig v1 fields byte-
semantically equal to the admitted CA-C state. In particular, `enabled` and
`require_admission_receipt` are protected CA-C/policy values, not linkage
defaults. A current body that already equals the target is a physical no-op;
any other protected-field drift, missing successor binding, same revision with
different body, or final CA-C status/history mismatch is `STOP / EFFECT0`.

### 4.7 PL-B secretary pre-execution Gate route

The current Codex task inventory contains the exact recipient task titled
`秘書`, thread `01a004a9-a34d-7f20-b5d1-4805690d6804`, on the BAI Development
OS project. Existing completed receipts establish this storage protocol:

1. send the committed runbook original without rewriting or summarizing it;
2. store the original and receipt metadata as separate artifacts;
3. compute and read back UTF-8 byte count and SHA-256;
4. return `read-back=MATCH`, saved path, document identity, and receipt identity
   to the source task; and
5. add or bind a central-index/addendum entry without treating storage as
   execution authority.

The currently readable central base index is
`BVP-PROCEDURE-ORIGINAL-CENTRAL-RECEIPT-INDEX`, file SHA-256
`1b929491848d5fc11bb36e3246334ab33ebbd4603abacb507eea83fbf58f7fb4`.
Later addenda are separate identities, so that base hash is historical routing
evidence, not the future PL-B receipt.

No TASK-065 runbook is sent now: D0-D2 and the executable transaction are not
closed, so an exact command or screen operation would be invented. Before the
first future config/native effect, PL-B requires a committed task-local runbook
containing target, purpose, source/version/hash, prerequisites, exact operation,
changed coordinate, verification, rollback/cleanup, and secret exclusion, plus
a completed secretary response with independent `MATCH`. A queued, sent-only,
unread, stale, or mismatched secretary record remains `NO_GO / EFFECT0`.

### 4.8 Windows namespace publication is not target-identity CAS

Microsoft's current Win32 and file-system protocol documentation closes the
remaining publication-semantics question:

- [`CreateFileW`](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)
  keeps each handle's sharing options in force until close. Omitting
  `FILE_SHARE_WRITE` or `FILE_SHARE_DELETE` prevents a later conflicting write
  or delete/rename open rather than conditionally allowing it against an
  expected file identity.
- [`FILE_RENAME_INFO`](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_rename_info)
  can replace an existing target and can resolve a relative target name from a
  directory handle, but its target condition is only existence. It has no
  expected target file ID, expected byte hash, or expected logical revision.
- [`FileRenameInformation`](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fscc/1d2673a8-8fb9-4868-920a-775ccaa30cf8)
  reports access denied when the source handle lacks delete access or an open
  target conflicts with replacement. Holding the admitted old target without
  delete sharing therefore blocks replacement; it does not turn replacement
  into a compare-and-swap.
- With
  [`FILE_RENAME_POSIX_SEMANTICS`](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fscc/4217551b-d2c0-42cb-9dc1-69a716cf6d0c),
  existing handles to the replaced file remain valid while subsequent opens of
  the same target name resolve to the renamed file. A pre-opened handle can
  consequently attest the old object while the namespace already names a new
  object.
- [`ReplaceFileW`](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilew)
  opens the replaced pathname with read/delete/synchronize access and all three
  share modes. It accepts no expected target identity or content parameter.
  Its documented failure outcomes can also leave the replaced or replacement
  file deleted, renamed, or carrying inherited streams/attributes rather than
  guaranteeing rollback to the original two-name state.

The resulting TASK-065 inference is deliberately narrower than claiming a
general Windows limitation: the documented rename/replace operations available
to this design provide atomic-style namespace publication, but do not by
themselves provide a CAS predicate bound to the previously read target File ID,
body hash, and CA-C revision. A handle that denies the conflicting access makes
publication fail; a handle that permits replacement can remain bound to the old
object after the name changes.

Accordingly, current PL-B cannot claim hostile-writer-safe CAS while the
installed SKILL root grants Modify to multiple principals and one writable SID
remains unresolved. Before mutation authority can open, the canonical contract
must supply all of the following:

1. an exact allowed-writer set and disposition for every writable ACE,
   including the unresolved SID;
2. either exclusive namespace write ownership for the bounded transaction or a
   cooperative lock/revision protocol honored by every allowed writer;
3. a closed transaction that validates CA-C logical predecessor, admitted
   instance, complete ancestor chain, target bytes/File ID/DACL/link count,
   same-directory `CREATE_NEW` temporary identity and bytes before publication;
4. an explicit fail-closed/recovery result for every documented partial
   `ReplaceFileW` outcome and process interruption point; and
5. post-publication reopen-by-name verification of exact bytes, new File ID,
   DACL/link/ancestor state, CA-C status/history, and config revision.

Post-publication read-back is bounded evidence, not permanent exclusion of a
later authorized write. Every future connector consumer must revalidate the
current revision/body/instance coordinate at use time. Without exclusive or
cooperative writer authority plus that consumer revalidation contract, the
result is `CONFIG_NAMESPACE_CAS_UNPROVEN / STOP / EFFECT0`.

### 4.9 Installer lifecycle currentness is not descriptor discoverability

The current TASK-063 source gives a precise lifecycle boundary:

- the Inno Setup package has one fixed `AppId` and `UsePreviousAppDir=yes`.
  This supports normal same-application repair/upgrade at the remembered root;
  it does not define a side-by-side active-instance registry or selector;
- `provision_installed_bridge(root, ...)` preserves the instance ID and
  `created_at` when a valid descriptor exists, updates the manifest digest and
  `updated_at`, and then discovers the same caller-selected root;
- `discover_installed_bridge(root)` validates only that root's descriptor and
  owner binding. It does not prove the installed Product EXE/payload, installer
  registration, uninstall state, or uniqueness across other roots;
- the public discovery receipt omits the installer manifest digest and absolute
  root. It is public-safe, but its descriptor hash must be cross-bound to the
  private descriptor and an independent current Product-installation receipt;
- Bridge data is intentionally outside installer-owned recursive deletion, and
  no `[UninstallDelete]` section exists. The real uninstall was not executed in
  TASK-063 acceptance, so preservation is source intent until PL-D runtime
  read-back; and
- the installed SKILL/config is outside the BVP installer root. Product
  upgrade/uninstall cannot by itself update or disable that external config.

Focused read-only/source-fixture confirmation produced:

- `tests/test_task063_main_installer_contract.py`: `3 passed`;
- a temporary two-root lifecycle probe: `PASS` — distinct roots minted distinct
  instance IDs, same-root repair preserved ID/created time while advancing the
  manifest, and discovery still returned `READY_DISABLED_BY_DEFAULT` when no
  Product EXE existed; and
- the combined TASK-063 Python test module was `NOT RUN` after collection was
  blocked by the available WSL `cryptography` lacking `Argon2id` through an
  unrelated TASK-036 import chain. No dependency was installed and this is not
  reported as PASS or as a TASK-063 behavior failure.

Consequently, an uninstalled or superseded root can retain a valid descriptor,
owner manifest, receipts, Profiles, and discovery result while no longer being
the current executable installation. Reinstalling the same preserved root may
also legitimately reuse the instance ID, but only a predecessor/current
installer receipt chain can distinguish continuity from stale resurrection.
TASK-065 must classify descriptor-only discovery as
`INSTALL_CURRENTNESS_UNPROVEN`, never select it implicitly, and never delete its
preserved learning data.

The PL-D current-instance coordinate therefore needs an exact tuple of
installer-selected opaque instance ID, descriptor self-hash and physical
identity, installer payload/tree digest, Product EXE/payload identity,
installation registration/currentness receipt, Bridge owner identity, and the
CA-C config/history revision that names the same relative Bridge. Absolute root
text stays local/private; the public result exposes only opaque instance and
relative coordinate. Zero or more than one current tuple is fail-closed.

## 5. Fresh installed-instance read-back

The bounded TASK-063 test installation was reopened read-only. Its public-safe
file hashes and semantic identities remain unchanged from the PL-A freeze:

| Artifact | Current file SHA-256 | Current semantic identity |
|---|---|---|
| `bridge-instance.json` | `0a28c3ecc37432665331d9cf0e6ef7b9b905671cbf7b03d6a030e34276ceb4a2` | `sha256:a51009d5d8fa509afd5f3528caf17f3bd0ce39d39d3d4bf2d605bebed0265ece` |
| `bridge-owner.json` | `90b5b18bcd732fd4139ace2c79a481f1a659422605e405ad4ab3c783fd7cea56` | `sha256:e141c94c6ca751edba9e9345a1f8570c324b3d1601527bd0d06e5340172272e6` |
| `migration/installer-readback.json` | `8fae5fdd9e2f0e38d38a887fd4e97c65d1dab36b00a2627997480d85433ce9fd` | exact descriptor/owner identities above |

The instance remains
`bvp-install-a65cf0984a214bdab781912f56c7c88f`, status
`READY_DISABLED_BY_DEFAULT`, with connector and activation false. `fsutil`
reports one name for each public artifact. The inspected chain from the volume
root through the migration directory reports no link target or reparse-point
attribute. The Bridge DACL remains protected with FullControl for Owner Rights,
SYSTEM, and Administrators.

These are present-time observations only. They do not close the source races,
prove uninstall/upgrade behavior, or satisfy D0.

## 6. Independently re-evaluable arrival deltas

In addition to the checklist in the PL-A design freeze:

### D0 delta

- [ ] descriptor and owner are reopened and cross-bound immediately before
  receipt publication;
- [ ] existing receipt descriptor transition is explicitly validated;
- [ ] existing-target final replacement is handle-bound or otherwise proven
  collision-safe;
- [ ] new-target link cleanup failure has a defined fail-closed outcome;
- [ ] every existing ancestor above and below install root is covered at each
  callable boundary;
- [ ] `ssPostInstall` rechecks the complete ancestor identity before execution;
- [ ] packaged read-back recomputes descriptor/owner hashes and records stable
  physical identities.

### D1/D2 design-source delta

- [ ] accepted design body is reachable and digest-verifiable from canonical
  coordinates, or a canonical superseding rebind exists;
- [ ] PP-C and CA-C fields are frozen only from their actual released closed
  source/schema/receipt, never from the PP-A candidate or allocation prose;
- [ ] TASK-061 readiness dependency text matches the released public-v1/private-
  diagnostic split before CA implementation.

### PL-B CAS delta

- [ ] CA-C supplies an exact config revision/body hash and append-only history;
- [ ] current SKILL config byte/physical identity is separately captured;
- [ ] the admitted TASK-063 instance is unique and current;
- [ ] DACL/reparse/hardlink/ancestor policy is current before and after the
  separately gated config transaction.
- [ ] every writable ACE resolves to a canonically allowed writer; the current
  unresolved Modify SID is removed or explicitly bound by the owning security
  authority rather than trusted by presence;
- [ ] exclusive namespace write ownership or an all-writers cooperative
  lock/revision protocol closes the read-to-publication race;
- [ ] failure/recovery behavior covers every documented non-original
  `ReplaceFileW` outcome and process interruption point;
- [ ] post-publication reopen-by-name proves exact config bytes, File ID,
  DACL/link/ancestor state, CA-C status/history, and revision, and the connector
  revalidates that bounded evidence before use;
- [ ] CA-C defines and authenticates the coordinate-only successor/composition
  rule so PL-B does not invalidate Human activation authority by changing the
  whole-file hash;
- [ ] PL-B leaves the canonical/installed distribution config unchanged and
  projects a separate BVP-owned runtime config at the admitted instance-relative
  coordinate; that projection requires `require_admission_receipt:true`, while
  `enabled` and the two transport feature flags are operation-scoped and
  least-privilege rather than copied as an always-on pair.
- [ ] committed PL-B runbook original is stored by secretary task
  `01a004a9-a34d-7f20-b5d1-4805690d6804` and an independently read-back
  UTF-8 byte count/SHA-256/receipt identity returns `MATCH` before any effect.

### PL-D lifecycle delta

- [ ] custom Unicode/space root binds one opaque instance, relative Bridge,
  descriptor/owner identities, current Product payload and installer receipt;
- [ ] same-root upgrade preserves instance/created time, advances payload and
  descriptor identities, and supplies a predecessor/current receipt chain;
- [ ] two independently provisioned roots produce two distinct candidates and
  admission returns `MULTI_INSTALL_AMBIGUOUS`, with no implicit winner;
- [ ] uninstall runtime read-back proves Product payload removal and Bridge
  learning/receipt/Profile preservation without treating the preserved
  descriptor as current;
- [ ] reinstall/repair after preserved data proves explicit continuity before
  reusing the instance; otherwise the instance remains stale/effect0;
- [ ] upgrade/uninstall/config drift triggers CA-C-owned disable/history
  read-back before any connector use; TASK-065 does not synthesize activation
  or deactivation authority;
- [ ] stale descriptor, stale installer manifest, missing Product payload,
  unknown registration, config naming another instance, or zero/multiple
  current candidates returns disabled/effect0 and preserves all learning data.

## 7. Public-safe PL-C fixture identity chain

The released TASK-058 adapter E2E supplied the historical synthetic body
`MontageLearningExport` record `e2e-observation-001`. It contains synthetic
proposal/timeline/style/event data and declares `privacy.safe_export:true`.
**SUPERSEDED:** that fixed flag and a fixture review are audit Evidence only,
not Production privacy authority. Current admission additionally requires the
independent closed privacy-projection completion receipt defined in
`pl-b-option-b-runtime-config-design-correction-2026-08-31.md`; no raw actor,
absolute host path, transcript, credential or media body may cross that
validated boundary, and `adapter_metadata.canonical_timeline:false` remains
mandatory.

### 7.1 Exact current SKILL lineage

The canonical SKILL remote `main` is currently
`45069b05b222b4be33b144f297cac67db0627df9`. The authoring worktree is on a
different dirty branch and was not switched, fetched, or modified; the exact
remote-main object was read from the clean local mirror. All six PL-C-relevant
installed files are byte-identical Git blobs to that exact remote commit:

| Role | Installed bytes | Installed/remote SHA-256 |
|---|---:|---|
| `SKILL.md` | 10257 | `1a7ba2d4967cfc7bf30b5d9f64cadf77bd9b19e558a7bd11c92d9161cb9c6308` |
| connector config | 406 | `da41b71292fd2a9fa2070eba531e06fafc0e84f9bbc1d26c27b0af79c5e2db6c` |
| connector bridge reference | 4758 | `669d34b4788493bb851149522d0beac1bc4a46c5f9e0b5b7b96bcab6c9faeee2` |
| connector schema | 5812 | `470fb97a85bb924678e51a9fca313c21bc5eb9c6eb0f0f0da265ca9b6da43b9d` |
| adapter script | 53438 | `070d2295869cb43c9fe8cb733238ff04085fa6815ac006385072d9c18da3949e` |
| adapter focused tests | 19323 | `b91f3e0d6d638d263e48812144462338238c70543899612fc82e12da4f8a8b36` |

The unchanged source still documents and defaults to fixed ProgramData. That is
legacy distribution evidence, not an admissible TASK-065 production fallback.
PL-C must select the PL-B-synchronized installed config explicitly and prove its
current physical identity; omission of `--config`, reinstall/upgrade reset, or
default-config reversion is `STALE_CONFIG_COORDINATE / STOP / EFFECT0`.

### 7.2 Required independent identities

The future PL-C test may reuse the semantic shape but must generate its own
task-scoped record identity. It must record five distinct evidence identities:

1. **Request/delivery identity** — canonical SHA-256 of the exact
   `MontageLearningExport`, plus a byte hash of the closed
   `BvpMontageLearningDelivery` whose `record_id` and `learning_sha256` match,
   and whose `canonical_timeline` and `auto_admit_authorized` are false.
2. **Public SKILL receipt identity** — exact seven-field v1 public receipt bytes
   hash, deterministic `receipt_id`, matching `record_id` and
   `learning_sha256`, and status `ACCEPTED` or `DUPLICATE`.
   **SUPERSEDED:** the former two-call interpretation (PENDING stage followed by
   a second `publish-learning` confirmation returning
   `canonical_store_written:true`) is prohibited because it can recreate the
   claimed inbox delivery. The current sequence is adapter stage exactly once
   (PENDING allowed), TASK-036 exact `import_path`, then a separate trusted BVP
   pinned receipt/correlation/canonical/Profile read-back. The public receipt
   and `canonical_store_written` remain transport audit Evidence with
   `authority_created:false`.
3. **BVP review-observation correlation identity** — exact hidden
   `BvpMontageLearningGenericReceiptCorrelation` self-hash and public-receipt
   hash, bound to the source digest, generic store/revision, canonical commit,
   internal receipt, Project Manifest, child binding, and ledger head. Its
   authority fields must independently remain `learning_adopted:false`,
   `profile_promoted:false`, and `timeline_mutated:false`.
4. **PP-C profile publication identity** — the exact PP-C promoted envelope and
   source receipt must bind the immutable profile payload document hash, current
   pointer revision/self-hash/predecessor, marker, compatibility-view bytes,
   profile ID/version/hash, Owner scope, and source count.
   **SUPERSEDED:** the historical statement that `ProfileSourceBinding` exposed
   only unbound-production and bound-isolated-fixture constructors is no longer
   current; main now also exposes `bound_verified_production()` from a public
   `PromotedPreferenceSourceRead`. Both public objects/tokens/self-hashes are
   audit Evidence only and cannot create Production authority. D1 instead
   requires the trusted Product operation's durable pinned native-source
   completion plus private one-use publish capability, not something TASK-065
   may manufacture.
5. **SKILL profile read-back identity** — a separately invoked `load-profile`
   result whose profile ID, version, contract, hash, source count, and payload
   equal identity 4. The read-back must keep `advisory_only:true`,
   `canonical_timeline:false`, and `auto_apply_authorized:false`.

The BVP store read-back must independently show the synthetic source digest,
append-only entry membership, dedup behavior, `learning_adopted:false`,
`profile_promoted:false`, and `timeline_mutated:false`. A READY connector
status, file existence, process exit zero, or adapter-reported path is only a
precondition and never the runtime verdict.

### 7.3 Current adapter gaps that PL-C must close externally

The exact current script and tests show these deliberate distinctions:

- `connector-status` returns `READY` from directory existence alone. The CLI
  also exits zero for disabled or unavailable safe-fallback states, so PL-C must
  validate the JSON status and exact instance/config identities rather than the
  process exit code.
- the SKILL v1 receipt reader checks record/hash/status/id/time but permits
  additional fields and does not validate the BVP correlation. TASK-065 must
  apply the exact v1 field set and then verify identity 3 independently before
  treating the receipt as BVP runtime evidence;
- `load-profile` validates the closed delivery and projection payload hash, but
  it does not verify the PP-C source receipt, immutable payload, pointer,
  predecessor, marker, or current compatibility-view publication. Identity 4
  must be established first and compared to the separate SKILL result;
- `atomic_write_new_or_identical` checks pathname existence and then publishes
  with `os.replace`. Two writers can both observe absence, and the operation has
  no no-replace or expected-target identity predicate. The existing focused test
  covers sequential identical dedup only, not collision, multiprocess, DACL,
  reparse, hardlink, ancestor, or hostile namespace races.

The existing isolated synthetic happy-path E2E was rerun through WSL with
`BVP_TASK058_SKILL_ROOT` bound to the exact installed SKILL: `1 passed` in
7.27 seconds. It proves the already-documented fixture flow and installed input
immutability only; it is not production PL-C runtime, dependency completion, or
negative-race coverage.

Therefore append-only/dedup acceptance requires the PL-B allowed-writer and
namespace-exclusion/cooperative-lock conditions from section 4.8, plus exact
delivery reopen-by-name read-back and BVP idempotent store/correlation proof.
Any conflicting body at the same derived pathname, disappearance or identity
drift during publication/read-back, extra public-receipt field, missing or
invalid correlation, or PP-C pointer/source mismatch is fail-closed. TASK-065
must not repair or reimplement the TASK-058 adapter contract to hide these
conditions.

This fixture is not runnable against the current installed production
coordinate: the released installed config is disabled, points to the absent
fixed ProgramData root, and does not require a receipt. PL-C execution remains
gated on D0-D2, PL-A PASS, PL-B coordinate synchronization, and the inherited
CA-C activation history.

## 8. Current result and next safe work

Fresh dependency re-evaluation at parent checkpoint
`81e65a8c46c080f4b25f78b7f0e146a7540bab67` found no arrival or identity
change: canonical `main`, PR #448, PR #430, and TASK-061 remain at the states
recorded above.

- D0: `BLOCKED_PR448_NOT_CANONICAL_AND_RESIDUAL_BOUNDARIES_OPEN`.
- D1: `BLOCKED_PP_A_DRAFT_PP_B_PP_C_ABSENT_DESIGN_BODY_UNREACHABLE`.
- D2: `BLOCKED_CA_UNAUTHORIZED_CA_C_ABSENT_CONTRACT_DRIFT_DESIGN_BODY_UNREACHABLE`.
- PL-A source/schema/test implementation eligibility: `FALSE`.
- Installed config/native/adapter execution eligibility: `FALSE`.
- Overall effect: `0`.

The next safe re-entry action is read-only currentness evaluation of exact D0,
D1, and D2 receipts. If no dependency identity changes, only the synthetic
fixture assertions and failure classifications already frozen are runnable;
creating those test files remains prohibited until D0-D2 are complete.
