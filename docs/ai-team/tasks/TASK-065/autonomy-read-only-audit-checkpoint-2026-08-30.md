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

## 7. Public-safe PL-C fixture identity chain

The released TASK-058 adapter E2E already supplies a suitable synthetic body:
`MontageLearningExport` record `e2e-observation-001`. It contains only synthetic
proposal/timeline/style/event data, declares `privacy.safe_export:true`, carries
no raw actor, absolute host path, transcript, credential, or media body, and
keeps `adapter_metadata.canonical_timeline:false`.

The future PL-C test may reuse the semantic shape but must generate its own
task-scoped record identity. It must record three distinct evidence identities:

1. **Request/delivery identity** — canonical SHA-256 of the exact
   `MontageLearningExport`, plus a byte hash of the closed
   `BvpMontageLearningDelivery` whose `record_id` and `learning_sha256` match,
   and whose `canonical_timeline` and `auto_admit_authorized` are false.
2. **BVP receipt identity** — exact public receipt bytes hash, deterministic
   `receipt_id`, matching `record_id` and `learning_sha256`, and status
   `ACCEPTED` or `DUPLICATE`. `publish-learning` must first report
   `STAGED_PENDING_REQUIRED_RECEIPT`, then only after BVP processing report
   `BVP_REPORTED_ACCEPTED` or `BVP_REPORTED_DUPLICATE` with
   `canonical_store_written:true`.
3. **Profile publication/load identity** — exact closed
   `BvpMontagePreferenceProfileDelivery` bytes hash and `profile_sha256`, then
   an independently invoked `load-profile` result with equal profile ID,
   version, contract, hash, source count, and payload. The read-back must keep
   `advisory_only:true`, `canonical_timeline:false`, and
   `auto_apply_authorized:false`.

The BVP store read-back must independently show the synthetic source digest,
append-only entry membership, dedup behavior, `learning_adopted:false`,
`profile_promoted:false`, and `timeline_mutated:false`. A READY connector
status, file existence, process exit zero, or adapter-reported path is only a
precondition and never the runtime verdict.

This fixture is not runnable against the current installed production
coordinate: the released installed config is disabled, points to the absent
fixed ProgramData root, and does not require a receipt. PL-C execution remains
gated on D0-D2, PL-A PASS, PL-B coordinate synchronization, and the inherited
CA-C activation history.

## 8. Current result and next safe work

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
