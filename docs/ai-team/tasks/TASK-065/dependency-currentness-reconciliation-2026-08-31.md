# TASK-065 dependency currentness reconciliation

State: `DEPENDENCY_DELTA_V2 / TASK_LOCAL_DESIGN_ACTIVE / SOURCE_START0 / EFFECT0`

Audit base: `origin/main = 35cdf1ad475633dcf035e0616e979b5a8fde0c88`

Current checkpoint: `2026-08-31 / v2`. Worktree and PR observations below are
read-only currentness cells, not canonical completion receipts or authority.

This task-local read-only reconciliation supersedes only stale missing-source
classifications in earlier TASK-065 design freezes. It does not rewrite their
historical observations, promote a candidate to PASS, authorize PL-A source, or
write shared task/index/roadmap/current-state metadata.

## 1. Fresh dependency classification

| Gate | Current read-only cell | Missing completion/currentness | Admission |
| --- | --- | --- | --- |
| D-068 / TASK-068 | corrected design is `IMMUTABLE_ONLY_V1`; canonical main still has no TASK-068 source/test and implementation receipt is N.C. The safe primitive scope is strict/pinned single-file read, secure lock, immutable single-file no-replace publish and durability only. It does not commit a directory tree and cannot advance a fixed phase journal | completion receipt separately proves `PINNED_READ_PASS`, `LOCK_PASS`, `IMMUTABLE_NOREPLACE_PASS`, `DURABILITY_PASS` and fixes `MUTABLE_CAS_UNAVAILABLE / MUTABLE_PHASE_ADVANCE_UNAVAILABLE / EXACT_DELETE_UNAVAILABLE / CURRENT_HEAD_AUTHORITY_NOT_CREATED / DIRECTORY_TREE_COMMIT_AUTHORITY_NOT_CREATED`, `authority_created:false`, `currentness_selected:false`. Each consumer must supply its own trusted exact generation/head plan, directory/container commit and tombstone semantics; no TASK-068 unit PASS promotes a consumer | `IMMUTABLE_ONLY_V1 / IMPLEMENTATION.N.C. / DIRECTORY_TREE_COMMIT_AUTHORITY_NOT_CREATED / MUTABLE_PHASE_ADVANCE_UNAVAILABLE / PL_B_SOURCE_START0 / EFFECT0` |
| D-069 / TASK-069 | negative/currentness matrix is prepared; source has not started and waits for TASK-068 completion. Current `origin/main=35cdf1a` logical tests are historical regression inputs, not Production readiness. Pending cleanup is path-unlink based. Profile payload publication is already content-addressed and immutable, but PREPARED through READBACK_VERIFIED rewrite one fixed journal; pointer/current-view/marker are fixed mutable targets; terminal unlinks the journal; recovery uses journal absence then the fixed pointer as currentness | after TASK-068, implement FB-R/C/P/PR/DUR, PRIV and READY. Pending uses plan-bound terminal tombstone precedence. `T69-PROFILE-CONTROL-GENERATIONS` retains immutable payload publication but migrates each phase, pointer transition and marker to immutable operation generations with predecessor hashes and a trusted exact BVP plan coordinate; current-profile v1 is derived display-only, terminal is immutable tombstone, physical old phases remain, and resolver precedence is exact terminal > exact phase > fresh without scan-highest/pointer/delete | `PROFILE_PAYLOAD_IMMUTABLE_PUBLISH CANDIDATE_PASS / T69-PROFILE-CONTROL-GENERATIONS HIGH.N.C. / CURRENT_HEAD_AUTHORITY_NOT_CREATED / PENDING_TOMBSTONE_RESOLVER.N.C. / START0 / TASK058_PRODUCTION_BASELINE.N.C. / EFFECT0` |
| D0 / TASK-063 | `READ_ONLY_MATRIX_REFINEMENT`: reusable historical tests cover Unicode/custom roots, repair identity preservation, tamper/link/ancestor/concurrency/read-back/rollback cases, fixed-ProgramData literal zero and installer-selected lifecycle contracts. They also explicitly update `bridge-instance.json` and `installer-readback.json` at their fixed targets, require repair to change `updated_at`, assert the update target remains the same path, restore predecessor bytes on update failure and remove both fixed files on fresh failure. Those mutable overwrite/restore/delete expectations are incompatible with TASK-068 `IMMUTABLE_ONLY_V1` and are legacy regression only. `discover_installed_bridge` is a logical read candidate, but packaged `discover` always calls `write_installer_readback`; its positive test requires the fixed readback file, so `T63-PACKAGED-DISCOVER-EFFECT0` is High current FAIL. Descriptor absence can also reuse an owner instance and path-unlink an old receipt. Directory durability may suppress failure. Inno acceptance trusts exit0 plus readback existence/ancestor equality and a build-input manifest without strict installed-byte/identity proof. GF-D PR #469 remains independently parked, Montage mutation is zero and TASK-068 is incomplete | independently park TASK-068 and GF-D #469. `T63-IMMUTABLE-INSTALL-GENERATION` publishes operation/install-instance-bound descriptor/readback generations no-replace. `T63-INTERNAL-DISCOVERY-READONLY` must become a trusted effect-zero route over one pinned descriptor+owner snapshot, compare it to a durable previously published installer receipt, and bind `DISCOVERY_READONLY=true / INSTALLER_READBACK_PUBLISH=false`; name/exit0 inference0. Missing/tampered/mixed state returns receipt0, inventory delta0 and path-free output. A trusted installer/launcher receipt supplies the one exact current coordinate; scan-highest, timestamp winner, caller coordinate and mutable pointer are zero. Also close strict JSON, physical races/lock, installed payload proof, native durability, lifecycle/multi-install/portable/uninstall read-backs and canonical completion receipt | `T63-INTERNAL-DISCOVERY-READONLY CANDIDATE_ONLY / T63-PACKAGED-DISCOVER-EFFECT0 HIGH.FAIL / PL_A_EFFECT0 / SOURCE_START0` |
| D1 / TASK-060 | `START0`: waits for TASK-068 and TASK-063 receipts; older worktrees are clean/merged but are neither reused nor deleted. Current PP-B uses one fixed `preference-promotions.json`, rewrites the full encrypted history by same-path replace and tests revision/rollback/crash/cross-process behavior against that fixed file. Those tests are legacy regression only and cannot prove an immutable consumer migration. Current duplicate also precedes source/policy/currentness validation | `T60-IMMUTABLE-GENERATION-MIGRATION`: publish each operation-bound encrypted revision generation no-replace with revision/hash/predecessor; select the exact current head only from a trusted Product operation/monotonic anchor; rollback appends a new generation bound to its target; preserve orphan/foreign/old generations and use exact plan-bound resume/tombstone semantics with scan-highest/pointer/delete zero. Also require trusted Human challenge, fixed DPAPI/Product coordinates, strict outer/decrypted JSON, fresh pinned current source/policy/backend/user/physical identity and private Profile read-back completion | `IMMUTABLE_GENERATION_MIGRATION.N.C. / DUPLICATE_CURRENTNESS_UNPROVEN / PROFILE_CAPABILITY0 / START0 / EFFECT0` |
| D2A / TASK-061-A PREACTIVATION PREPARE | `START0`: waits for TASK-068, TASK-069, TASK-063, TASK-060 and SKILL-D2S-001; this phase closes only the `enabled:false` prepare contract. Current CA-A writes PREPARED/COPIED/SNAPSHOT_COMMITTED/READBACK_VERIFIED into one fixed journal and commits a staging directory with `os.replace`. TASK-068 single-file primitives cannot advance that journal or authorize directory-tree commit | TASK-061-A owner must close all A61 gates plus `A61A-IMMUTABLE-PHASE-JOURNAL` and `A61A-DIRECTORY-NOREPLACE-COMMIT`: operation-bound pinned staging, native directory no-replace or immutable container manifest, immutable phase generations with predecessor hash and trusted exact selector, publish-before-selector orphan preservation, same-operation resume only, foreign delete0. Then issue one PREACTIVATION PREPARE receipt with real-E2E/activation claims zero; no TASK-068/public plan/snapshot/readback substitute | `START0 / A61A-DIRECTORY-NOREPLACE-COMMIT HIGH.N.C. / A61A-IMMUTABLE-PHASE-JOURNAL HIGH.N.C. / PREPARE_AUTHORITY.N.C. / P0_COMMIT_STOP / EFFECT0` |
| D2B / TASK-061-B FINAL CA-C | `START0`: waits for the TASK-036 real-installed E2E receipt. Initial config publication can overwrite a target that appears after the absence check, existing fixed config has no physical-currentness protection, and publication precedes final security/readback and may leave visible mutation with receipt0. Duplicate handling also treats the fixed history tail as the implicit winner and returns a reconstructed receipt before expected-revision, caller-time and final security/currentness checks (`A61-B-INITIAL-CONFIG-NOREPLACE`, `A61-B-EXISTING-CONFIG-IDENTITY-CAS`, `A61-B-POSTCOMMIT-FAILURE`, `A61B-IMMUTABLE-DUPLICATE-TERMINAL`) | consume the exact TASK-036 receipt, revalidate trusted time/currentness and close final CA-C while retaining `enabled:false`; migrate config/history and per-operation terminal receipts to operation-bound immutable generations with no-replace publication and consumer-owned exact head coordinates. Duplicate pinned-reads the exact operation terminal receipt/body/physical identity and committed Product timestamp; event-tail scan, receipt reconstruction, caller `now`/revision, pointer, scan-highest and delete are zero. Missing terminal state resolves only through its exact journal/tombstone. Activation visibility commits only with Human consume plus final security/readback, or remains an explicit plan-bound immutable pending/tombstone state. Production Activation remains a separate Human Gate | `START0 / WAITS_TASK036_E2E / A61B-IMMUTABLE-DUPLICATE-TERMINAL HIGH.N.C. / DUPLICATE_CURRENTNESS_AUTHORITY_NOT_CREATED / EFFECT0` |
| D2.5 / SKILL-D2S-001 Production transport | **SUPERSEDED source-reference wording:** the foreign `installer-relative-learning-bridge@c86ec8c` dirty eight-file worktree remains preserve-only and is not a receipt. Dedicated clean-main D2S Draft PR #8 now contains `7cdeef2`, `a99935d` and `6a39133`: strict bounded/pinned JSON, immutable/no-replace local delivery, closed privacy projection, data-only operation-config v2, and the `bridge_root:null` disabled sentinel. With `enabled:false`, `connector_status` returns before any Bridge path/availability probe. Neither canonical main/release/install exact read-back nor a BVP completion receipt exists | land/review the one coherent D2S PR, then require canonical main/release/install exact-byte read-back and a Product-owned completion receipt. PL-A rebind only after the released installed result | `D2S_SOURCE_DRAFT_PR8 / D2S-DISABLED-DISCOVERY0 SOURCE_COVERED / RELEASE_INSTALL_READBACK.N.C. / PARTIAL_HUNKS_ARE_NOT_RECEIPT / EFFECT0` |
| D2.5 / SKILL Product-operation authority | D2S PR #8 validates a closed operation-config v2 as data-only/evidence and keeps `authority_created:false`, but no adapter-consumed trusted broker/handle atomically redeems operation ID, TASK-061-A receipt, projection receipt, expiry, nonce, budget or TASK-063 instance. An enabled v1 config remains replayable/copyable and indistinguishable from steady state | Product-owned trusted broker/handle route with atomic one-shot redemption, immutable invocation-specific config/receipt coordinates, exact command/instance/input binding, replay/crash closure, release/install exact read-back and PL-A hash rebind; otherwise the TASK-036 preactivation attempt is internal synthetic-only and cannot produce real-installed E2E | `V2_DATA_ONLY_SOURCE_COVERED / PREACTIVATION_AUTHORITY.N.C. / EFFECT0` |
| D2.5 / SKILL publish confirmation | D2S PR #8 now validates a matching strict public receipt before staging and returns `BVP_RECEIPT_OBSERVED_TERMINAL_QUERY_REQUIRED` with `canonical_store_written:false`; receipt observation no longer triggers confirmation re-stage. It still has no hidden correlation/current canonical/Profile authority and is not a terminal Product receipt | TASK-036 exact-one stage followed by import and separate trusted BVP receipt/correlation/canonical/Profile read-back; no second publish; terminal status is read-only and broker-bound; canonical release/install/read-back before PL-A rebind | `NO_SECOND_PUBLISH_SOURCE_COVERED / TERMINAL_CORRELATION_PROFILE.N.C. / EFFECT0` |
| D2.5 / SKILL learning-export privacy | **SUPERSEDED:** generic bounded tokens were insufficient: actor/source/session/ID/style/context/tag values could launder player/account-like text, and caller redaction reports could omit mandatory markers. D2S `a99935d` replaces that draft with closed public codes, exact SHA-256 session digests, adapter-derived opaque IDs, and an exact derived redaction report. Focused adapter privacy coverage and an independent re-review report C/H/M/L=`0/0/0/0` are source Evidence only; BVP must independently validate the cross-process delivery | canonical D2S main/release/install exact-byte read-back and independent TASK-058/BVP closed privacy admission before pending/canonical/Profile effect; `safe_export`, public readiness and fixtures remain Evidence only | `CLOSED_SKILL_PRIVACY_SOURCE_COVERED / BVP_PRIVACY_ADMISSION.N.C. / RELEASE_INSTALL_READBACK.N.C. / EFFECT0` |
| D2.5 / SKILL strict JSON and Product I/O | D2S PR #8 supplies strict bounded UTF-8 parsing, pinned same-snapshot identity binding, local-only no-parent-create/no-overwrite legacy output, and disabled status with bridge-root/availability projection zero. The Product side still requires opaque-plan/handle-only I/O and an installed release/read-back | bind projection digest to the adapter's exact pinned parse through the trusted Product broker and prove canonical release/install exact bytes; retain body-free errors and prohibit Product raw config/learning/output paths | `STRICT_JSON_AND_LOCAL_OUTPUT_SOURCE_COVERED / D2S-DISABLED-DISCOVERY0 SOURCE_COVERED / PRODUCT_IO_BROKER.N.C. / EFFECT0` |
| D2.5 / TASK-058 File Bridge Production safety | released File Bridge remains canonical historical Evidence; current immutable publication, security-relevant reads, same-path import/Profile journals and pointer/current/marker state do not bind an external trusted current-head coordinate. Pending cleanup physically unlinks and the current loader would rediscover a retained pending record. Directory durability is a Windows no-op and the current test treats missing-directory success as platform-honest | separate TASK-058/TASK-069 owner correction with immutable plan-bound generations/tombstones, terminal correlation/tombstone > pending > fresh, restart recovery0/revision exact1/delete0, no mutable pointer or scan-highest, plus native directory durability and focused fault/Windows regression, canonical main/release/install exact read-back and downstream baseline rebind | `CURRENT_HEAD_AUTHORITY_NOT_CREATED / PENDING_TOMBSTONE_RESOLVER.N.C. / DIRECTORY_DURABILITY_UNOBSERVABLE / PRODUCTION_LINKAGE_N.C. / EFFECT0` |
| D2.5 / TASK-058 BVP privacy admission | generic delivery admission trusts key-name filtering and caller `safe_export:true`; benign-key values can carry paths, accounts, secrets or transcript-like content across the process boundary | independent closed per-contract BVP validator over every bounded string/value before pending/canonical/Profile mutation; controlled grammars, normalization-aware detectors, body-free errors and zero raw payload in temp/journal/receipt/log; canonical correction/install/read-back | `BVP_PRIVACY_ADMISSION.N.C. / EFFECT0` |
| D2.5 / TASK-058/TASK-060 Profile publish authority | public `PromotedPreferenceSourceRead` and `ProfileSourceBinding` token/self-hash objects can be caller-constructed and can reach the public prebuilt Profile publisher without a pinned actual promotion-source reread; `PromotedPreferenceSource` also accepts caller-provided cipher and coordinates, so synthetic/custom decryptors can launder a forged history unless Production composition fixes the backend | explicit cross-owner corrective authority; trusted same-open-snapshot encrypted source read; internally fixed Windows DPAPI backend and Product registry/manifest coordinates bound to selected-install owner/current-user attestation; private single-use late-bound Production publish capability; File Bridge ordered publication/readback correction and focused forgery/stale-source/backend tests | `AUTHORITY_AND_CIPHER_LAUNDERING.N.C. / EFFECT0` |
| D2.5 / TASK-058/TASK-061 readiness baseline | `production_readiness_evidence()` and public `ConnectorReadinessEvidence` accept caller state strings and E2E/default-config booleans; TASK-061 `_validate_public_readiness()` checks only exact type plus serialized field equality, and its positive fixture hand-enters the passing booleans without an executed adapter/package/installed-instance report | cross-owner durable `TASK058_BASELINE_READBACK` from a trusted Product reader pinning canonical release manifest/code/schema/test/package hashes, installed exact bytes, executed operation ID/build/config/request/result/BVP receipt/correlation/Profile read-back and current expiry; separate exact disabled-default predicate; TASK-061 fresh bind to TASK-063 instance, TASK-060 source and operation plan | `CALLER_ASSERTED_BASELINE.N.C. / EFFECT0` |
| D2.5 / TASK-067 | `PRESERVED_DIRTY / COMMIT_STOP`: at fresh `origin/main=35cdf1a`, canonical `docs/ai-team/tasks/TASK-067/`, TASK-067 remote branch and TASK-067 PR are all absent. The exact three-file candidate remains preserved, uncommitted and non-authoritative. Correlation outcome layering is narrow PASS. TASK-068 strict pinned immutable-read/existing-lock primitives are candidate-only for `VERIFIED_READBACK` and sealed terminal A2 lookup; TASK-067 still owns the exact current coordinate. `FRESH`, `PRECOMMIT_RESUME` and `JOURNAL_RECOVERY` need mutable Project/Generic transitions and exact terminal cleanup outside `IMMUTABLE_ONLY_V1` | canonical Task identity/owner/Allowed Files/dependency/C-H acceptance formalization; TASK-068/TASK-069, TASK-060/063 and corrected TASK-061-A PREACTIVATION PREPARE receipts; exact TASK-058/ProjectSave owner-preserving amendment; `T67-READBACK-NOCREATE`, `T67-A2-JOURNAL-ABSENT-TYPED-DUPLICATE`, `T67-READBACK-PRIMITIVE-USE` and `T67-WRITE-MODES-VIA-T68` closure; factory effect declaration per mode; immutable Project manifest generations, Generic phase generations, marker/anchor transitions and terminal tombstone; fresh overlap/work-lock PASS; explicit implementation start, DEV-4 review and completion receipt | `CANONICAL_AUTHORITY.N.C. / T67-OUTCOME-LAYERING-CORRELATION PASS / T67-READBACK-PRIMITIVE-USE CANDIDATE_ONLY / T67-WRITE-MODES-VIA-T68 HIGH.N.C. / COMMIT_STOP / EFFECT0` |
| D2.5 / TASK-036 | `START0`: waits for TASK-061-A, TASK-063, SKILL-D2S-001 and TASK-067 receipts. Source confirms the actual chain `task036_shell.spec -> task036_windows_entry.py -> packaged_main()`, one-dir `COLLECT`, `console=False` and final `BAI Video Production.exe`; the only pre-desktop private dispatch is installer bridge. Montage dispatch and mixed/duplicate/unknown argv negatives are absent | packaged exact single-record route at `packaged_main`, frozen Montage entry/module and payload-tree inclusion contract, internally resolved installed EXE, private dispatch exact1 before probe/guard/shell/presenter with each 0 and installer/discover0, closed argv parser, real-installed execution plus durable body-free receipt/correlation/Profile currentness. Installer ordering, stdout/exit0/EXE presence are ineligible | `T36-PRODUCT-MONTAGE-DISPATCH P0.N.C. / T36-CLOSED-ARGV-NEGATIVES P0.N.C. / START0 / EFFECT0` |
| D2.5 / TASK-036 -> TASK-061-B chain | both canonical completion receipts are absent: TASK-036 has no T36-A/B/S/M/R/P/E packaged producer completion (including T36-P01-P14) and TASK-061-B has no A61-E/R/D/Z trusted consumer completion | first close TASK-036 packaged dispatch/binding/resolver/mode/frozen-inclusion/read-back/installed E2E; do not copy TASK-063's exit0+`FileExists` existence-only predicate or treat its build-input manifest/acceptance JSON as installed proof. Then TASK-061-B freshly pinned-recomposes that exact operation and closes evidence/currentness/Human durable transaction/zero-effect lifecycle. TASK-065 accepts only both canonical receipts bound together; producer receipt, public objects/hashes/seals, exit0/status/`canonical_store_written` and synthetic fixture alone are ineligible | `PRODUCER_CONSUMER_CHAIN.N.C. / PL_C_PASS0 / EFFECT0` |
| D3 / TASK-065 | `TASK_LOCAL_DESIGN_ACTIVE / SOURCE_START0`: PL-A PLA-I01-I20 plus PL65-A06/A07/A08, PL-B PLB-I01-I19 plus PL65-B00/B03/B04/B05, C/D PLC-I01-I16, PL65-C01a/C01b and PL-D D01-D12 are source-mapped. Public discovery/hash, build-input payload digest, path-bearing acceptance JSON, descriptor timestamps, fixed descriptor/readback paths, descriptor-absent owner-only state and current Windows durability no-op are not Product proof; packaged `discover` writes readback; no active-install selector exists | all upstream receipts; trusted zero/one/multiple registration; corrected noncreating reader; exact-selector-bound immutable descriptor/readback generation plus same-open owner and installed payload manifest/tree; Product EXE/payload; native directory-durability receipts; immutable no-replace transitions/tombstones plus consumer-owned exact head coordinate; trusted clock/session and predecessor/successor registration+payload revision propagated through PL-B, TASK-036, PL-C, TASK-061-B and PL-D. Fixed-target overwrite/restore/delete, mutable pointer/same-path CAS, scan-highest/newest and automatic cleanup are prohibited. Accepted implementation Gate and separate Activation Gate remain required | `PL_A_START0 / PL_B_START0 / PL_C_START0 / PL_D_START0 / SOURCE_START0 / EFFECT0` |

### TASK-063 historical regression versus corrective delta

Reusable historical coverage is limited to regression input: Unicode/custom
install roots and exact relative layout; repair preservation of
`install_instance_id`/`created_at`; descriptor tamper, unsafe directory,
symlink/hardlink, forged-root and ancestor drift; concurrent no-clobber,
post-write mismatch and exact safe single-link update; forged/missing
predecessor and fresh/update rollback fixtures; fixed-ProgramData active literal
zero; and installer-selected destination/reparse/uninstall-preservation source
contracts.

Corrective PASS still requires I63-R01 descriptor+owner same-open snapshot and
mixed-generation rejection; same bytes on a different inode at stat-open and
read-post seams; nested duplicate equal/different, NaN/Infinity, BOM/trailing/
control/depth/size rejection for descriptor, owner, readback and rollback
preimage; I63-L01 secure existing/initial operation lock with first-provision,
hardlink/reparse/DACL races; temp-close foreign swap; target swap immediately
before/after publish; directory-fsync failure with receipt zero; foreign-current
rollback preservation with delete/restore zero; and multi-install, portable
rebind, upgrade predecessor/current Product payload and real uninstall
preservation read-backs.

The existing fresh rollback fixture starts from a wholly empty Bridge state,
but `provision_bridge` creates directories/owner before descriptor/receipt and
rollback leaves them in place. The fixture asserts only descriptor/receipt
absence, so `PARTIAL_OWNER_PRESERVED` is already reachable and its full Bridge
inventory plus owner inode/body are unverified. It does not cover owner-only or
owner-plus-old-receipt retry, automatic owner instance reuse, receipt swap, or
rollback after receipt inode replacement. Those states require STOP+preserve
unless an exact predecessor/journal proves recovery and the cleanup target is
operation-owned.

Therefore existing tests create no TASK-063 corrective completion receipt.
TASK-068 and GF-D PR #469 remain independently parked.

### TASK-069 completion receipt floor

TASK-069 cannot promote the historical TASK-058 logical suite into Production
readiness. Its durable completion receipt must bind all of these in one current
Product-owned chain:

1. `FB-R`: same-open File Bridge snapshot, pinned ancestors and `nlink=1`;
2. `FB-C`: exact plan-bound immutable import journal generations, predecessor
   and terminal-tombstone recovery identity; same-path CAS zero;
3. `FB-P`: operation-owned temp, no-replace publication and post-publish pinned
   read-back;
4. `FB-X`: physical pending retention is non-authority; terminal correlation/
   tombstone outranks pending then fresh, and automatic delete is zero;
5. `FB-PR`: `PROFILE_PAYLOAD_IMMUTABLE_PUBLISH` may reuse the content-addressed
   payload primitive, but `T69-PROFILE-CONTROL-GENERATIONS` must bind immutable
   Profile phase-journal, pointer-transition, marker and terminal-tombstone
   generations plus trusted exact coordinate and physical read-back. The fixed
   current-profile view is display-only and journal unlink is zero;
6. `PRIV`: strict bounded closed privacy projection before canonical hash or
   any pending/canonical/Profile effect; and
7. `HEAD`: consumer-owned trusted exact generation coordinate; no caller path,
   mutable pointer, scan-highest/newest or implicit winner; and
8. `READY`: executed durable `TASK058_BASELINE_READBACK` binding canonical and
   installed exact bytes, operation/config identity, public receipt, hidden
   correlation, Profile read-back and expiry/currentness.

Public readiness documents/self-hashes, caller `safe_export:true`, isolated
fixtures, status strings and code presence remain audit Evidence with
`authority_created:false`. Until TASK-068 completes, TASK-069 remains
`SOURCE_START0`; until all eight bindings complete, TASK-065 PL-A and PL-C
remain N.C./PASS0 with Project/Bridge/Profile/config/history effect zero.

The canonical one-way dependency graph is:

```text
TASK-068 -> {TASK-069, TASK-063}
TASK-063 -> TASK-060
{TASK-069, TASK-060, TASK-063, SKILL-D2S-001} -> TASK-061-A PREACTIVATION PREPARE (enabled:false)
TASK-061-A -> TASK-067
{TASK-061-A, TASK-063, SKILL-D2S-001, TASK-067} -> TASK-036 real installed E2E
TASK-036 -> TASK-061-B FINAL CA-C
all completion receipts -> TASK-065 PL-A/PL-B/PL-C/PL-D
```

Any older whole-task TASK-061 prerequisite is SUPERSEDED. TASK-061-A contains
only the CA-A/B corrections and CA-C sealed plan/config candidate/challenge
contract. TASK-061-B alone consumes TASK-036 real-installed E2E. Production
Activation execution remains a separate Human Gate.

### SKILL-D2S dirty-overlap hunk admission

The dirty eight-file `installer-relative-learning-bridge@c86ec8c` worktree is
read-only audit input, not a branch-level adoption candidate. After fresh owner
disposition, a dedicated clean-main D2S task may manually reimplement these
concepts:

- preserve distribution `enabled:false`;
- represent no fixed bridge root as `null`, allowed only while disabled;
- reject `enabled:true` plus null root;
- return `DISABLED_LEGACY_SAFE` with directory-creation delta zero for disabled
  null-root status; and
- remove fixed-ProgramData positive tests and explain installer-selected
  relative root with no automatic legacy adoption.

It must not carry instructions to write an absolute root into installed
distribution config, enable both feature flags as normal operation, reuse
config v1 as steady/preactivation authority, omit explicit Product `--config`,
or promote directory-existence READY to synchronization/E2E. Strict pinned
JSON, operation-v2 ticket/consume, exact-one stage, closed privacy and strict
receipt/correlation/Profile work remain missing (`D2S-J/R/O/P/T/C/D/A/V`;
only F01/I01 are partial). The two dirty files
`BVP_IMPLEMENTATION_WORK_ORDERS.md` and
`BVP_SIDE_REQUIRED_FEATURES_DETAILED_PROPOSAL.md` are outside D2S Allowed Files
and require separate owner disposition. The managed-skill inventory is
intermediate and may be regenerated only after the final accepted diff.

Result: `PARTIAL_PRESERVE_CONCEPTS / COMPLETION_RECEIPT0 / SOURCE_START0`.

### SUPERSEDED historical canonical-to-installed SKILL baseline

**SUPERSEDED CURRENTNESS:** the clean comparison and exact hashes below record
the earlier installed baseline only. They do not describe the current dirty
D2S worktree, authorize adoption of its hunks or satisfy any completion/read-
back receipt. Current admission is the dirty-overlap cell and hunk rules above.

Read-only comparison against canonical SKILL
`origin/main=c86ec8c11724a3170d37e0fdc5a516979fcca703` found zero scoped
worktree differences under `skills/bvp-montage-learning-adapter/`. The current
installed distribution copy matches these exact canonical bytes:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `scripts/bvp_adapter.py` | 53438 | `070d2295869cb43c9fe8cb733238ff04085fa6815ac006385072d9c18da3949e` |
| `config/bvp-learning-connector.json` | 406 | `da41b71292fd2a9fa2070eba531e06fafc0e84f9bbc1d26c27b0af79c5e2db6c` |
| `schemas/connector-file-bridge.schema.json` | 5812 | `470fb97a85bb924678e51a9fca313c21bc5eb9c6eb0f0f0da265ca9b6da43b9d` |
| `references/connector-ready-bridge.md` | 4758 | `669d34b4788493bb851149522d0beac1bc4a46c5f9e0b5b7b96bcab6c9faeee2` |
| `SKILL.md` | 10257 | `1a7ba2d4967cfc7bf30b5d9f64cadf77bd9b19e558a7bd11c92d9161cb9c6308` |

Classification is `EXACT_UNSAFE_BASELINE_MATCH / PRODUCTION_LINKAGE_N.C.`:
the equality proves distribution currentness for the known baseline, not the
missing transport/reader/receipt-schema/Option-B documentation corrections.
None of these hashes may be reused as the future corrected release/install PASS;
that chain requires new canonical release identities and a fresh installed-copy
read-back.

The TASK-065 PL-A docs head `66537ed` is also an ancestor of main, but its
historical audit base and missing-source statements are not current facts. This
document replaces those reason codes with candidate-present/completion-missing;
it does not change the fail-closed outcome.

Earlier TASK-063 fixtures, hashes and native Evidence predate the canonical
`8fd17ed` correction set and cannot be reused as current D0 PASS. A future PL-A
read admits only the post-correction source contract plus freshly provisioned
installed Evidence and exact completion receipt.

## 2. Read-only PP-C field map candidate

Current TASK-060 `PromotedPreferenceSourceRead` supplies these candidate inputs
for later PL-A mapping:

- `source_id`, pinned `source_file_identity_sha256` and `store_id`;
- `owner_scope_sha256`;
- `promotion_revision`, `promotion_revision_sha256` and `history_sha256`;
- `profile_id`, `profile_version` and `active_payload_sha256`;
- exactly one detached `envelope` plus `envelope_sha256`;
- `readback_sha256` over the complete read-back body;
- fixed advisory-only, no automatic promotion, no Timeline/Resolve/external
  effect flags.

`PromotedPreferenceSourceRead` and its hashes are public audit Evidence only;
their exact type, token or self-hash never creates authority. After D1
completion, PL-A may bind only the durable pinned source-read completion receipt
from the trusted Product operation plus that operation's private currentness.
It rejects mutable/subclass/mapping substitutes, zero/multiple active envelopes,
stale file identity/revision/history/payload, Owner-scope drift or any
non-advisory authority. Reading current source now does not admit a Profile or
satisfy D1.

An exact TASK-060 promotion/rollback `DUPLICATE` is likewise ineligible. Current
source returns it before CAS and source/policy currentness checks, including the
tested stale `expected_revision=0` replay after revision 1. PL-A may record the
historical event as already committed with write delta zero, but it requires a
separate fresh trusted read of store revision/head, source/policy, ciphertext
physical identity, DPAPI backend/user and Profile coordinates. Revoked/drifted
source, policy drift, advanced/rolled-back store, same bytes/new inode or
backend/user drift yields `DUPLICATE_CURRENTNESS_UNPROVEN / PROFILE_CAPABILITY0`.

## 3. Read-only CA-B/CA-C field map candidate

Current TASK-061 candidate types expose the following potential PL-A inputs:

- `ConnectorSourceBindingReadiness`: binding/plan identity; target install
  instance; descriptor and owner-manifest hashes; security and migration
  read-backs; PP-C source/envelope hashes; TASK-058 public readiness v1 hash;
  profile ID/version/hash; publish status; final `binding_sha256`; fixed
  `SOURCE_BOUND_ACTIVATION_BLOCKED`, `connector_enabled:false` and
  `activation_authorized:false` flags.
- `InstalledAdapterE2EReadback`: target instance, source binding, connector
  status, publish receipt, Profile read-back and `adapter_e2e_sha256`. The
  current public admission rejects real-installed evidence, so this type is not
  a valid D2 completion receipt.
- `ConnectorActivationTransactionReceipt`: target instance, source binding,
  Human evidence, optional adapter E2E, revision, action/enabled state,
  `history_sha256`, `config_readback_sha256` and `transaction_sha256`, with
  repository default false and external SKILL config unchanged.

These public readiness/Human/E2E/transaction types, factories and self-hashes
are audit projections only, including factory-produced exact objects. Later
PL-A/CA-C effect authority requires a private one-use trusted Product-operation
capability plus durable pinned completion read-back and separately binds the
Option B runtime-config projection receipt. It must not treat the disabled
history candidate as activation or accept a transaction without the future
real-installed E2E and Human authority completions.

## 4. D2.5 explicit PL-C/CA-C prerequisite

Pre-activation E2E requires both current receipts:

1. TASK-067 Generic-only sealed current/fresh/recovery/readback facade; and
2. TASK-036 packaged exact single-record `import_path` entrypoint, selected by
   a closed headless dispatch and backed by a Montage-specific private
   composition. Public `Task036LaunchConfiguration`, raw paths/hashes/revision,
   caller-selected mode and full trusted-launch/Desktop lifecycles are not
   authority inputs.

TASK-067's preserved uncommitted source/test candidate is read-only audit
Evidence only. It is neither canonical source nor a dependency PASS and must
not be imported, executed, committed, pushed or used to unblock TASK-061/036/
065. The exact freeze and future start Gate are recorded in
`task067-candidate-allocation-and-freeze-packet-2026-08-31.md`.

## 5. Re-entry/currentness ledger

Each heartbeat or future implementation preflight evaluates these independently:

| Receipt | Identity/read-back requirement | Current |
| --- | --- | --- |
| TASK-068 foundation | `IMMUTABLE_ONLY_V1`: pinned single-file read, secure lock, immutable single-file no-replace and durability PASS; mutable CAS/phase advance, delete, current-head and directory-tree commit authority explicitly unavailable | implementation N.C. / receipt0 |
| TASK-069 | may start only from TASK-068 completion; immutable Profile payload is candidate-only while journal/pointer/view/marker/delete control remains outside TASK-068 | matrix prepared / `T69-PROFILE-CONTROL-GENERATIONS` High N.C. / START0 |
| TASK-069 Profile control | immutable phase journal + predecessor, immutable pointer transition/marker/terminal tombstone, trusted exact BVP plan coordinate and resolver terminal > phase > fresh; fixed current-profile display authority0, scan-highest/pointer/unlink0 | missing / PL-A/B/C Profile PASS0 |
| D0 completion | TASK-063 historical fixed-path overwrite/restore/delete and effectful packaged-discover coverage are regression input only; add `T63-IMMUTABLE-INSTALL-GENERATION`, `T63-INTERNAL-DISCOVERY-READONLY`, I63-R01/I63-L01, strict JSON, physical-race/durability, descriptor-absent immutable orphan/tombstone recovery and lifecycle read-backs after TASK-068 and GF-D #469 Gates | `T63-PACKAGED-DISCOVER-EFFECT0` High FAIL / read-only route missing / source START0 |
| D1 completion | independent DEV-4 PP-A/B/C acceptance including trusted Human promotion/rollback, secure PP-B store, internally fixed Windows DPAPI source, strict outer/decrypted authority JSON and exact PP-C read-back | missing/N.C. |
| D1 Profile authority | trusted pinned native source plus private one-use Production publish completion and ordered exact read-back | missing/N.C. |
| D2 whole-task completion | **SUPERSEDED:** one receipt cannot stand for prepare, real E2E and final CA-C | ineligible |
| D2 TASK-061-A | `enabled:false` CA-A/B corrections plus sealed CA-C plan/config/challenge PREACTIVATION PREPARE | START0 / waits TASK-068/069/063/060/D2S |
| D2 TASK-061-B | consumes TASK-036 real-installed E2E and closes final CA-C without Production Activation | START0 / waits TASK-036 |
| D2 TASK-058 baseline | trusted durable `TASK058_BASELINE_READBACK` freshly bound by TASK-061; public v1/V2 readiness is display-only | missing/N.C. |
| D2 CA-A terminal authority | private one-use currentness capability from pinned terminal migration journal plus exact snapshot manifest/tree/physical identities | missing/N.C. |
| D2 CA-A directory commit | `A61A-DIRECTORY-NOREPLACE-COMMIT`: operation-bound pinned staging tree plus Windows native directory no-replace commit or immutable container manifest; exact snapshot 0/1, foreign preserve/delete0 | High N.C. / TASK-068 receipt ineligible |
| D2 CA-A phase journal | `A61A-IMMUTABLE-PHASE-JOURNAL`: PREPARED and each successor are immutable generations bound by predecessor hash and trusted exact plan/recovery selector; scan-highest/mutable fixed journal/delete0 | High N.C. / TASK-068 receipt ineligible |
| D2 CA-A/CA-B execute authority | separate trusted durable one-shot action tickets; deterministic public confirmations and raw public executors are ineligible | missing/N.C. |
| D2 trusted time | Product/OS-owned clock domain spans issue/receipt/apply/consume/read-back and Product-authors history timestamp; caller `now` is ineligible | missing/N.C. |
| D2 strict authority JSON | bounded duplicate/non-finite/BOM/trailing/control rejecting same-snapshot parser for CA-A/CA-B/CA-C durable state | missing/N.C. |
| D2 CA-A producer gate set | all `A61-*` authority, transaction, snapshot, temp/staging ownership, security, terminal receipt/currentness/privacy and early resource-ceiling rows in the task-local matrix | P0/P1 open / PREPARE receipt ineligible |
| D2 CA-B activation config transaction | `A61-B-INITIAL-CONFIG-NOREPLACE` and `A61-B-EXISTING-CONFIG-IDENTITY-CAS` closed by immutable generation migration: no-replace publish plus trusted exact head/predecessor receipt, with same-path CAS/pointer/scan/delete0 | P0 open / Activation PASS0 |
| D2 CA-B activation terminal commit | `A61-B-POSTCOMMIT-FAILURE` closed so ACTIVATE enabled visibility cannot survive a final security/readback failure without a trusted terminal receipt | P0 open / Activation PASS0 |
| D2 CA-B immutable duplicate terminal | `A61B-IMMUTABLE-DUPLICATE-TERMINAL`: operation-specific immutable terminal receipt, trusted exact coordinate, pinned same-body/physical-identity readback and exact journal/tombstone recovery; fixed history tail, caller time/revision and reconstructed receipt authority0 | High N.C. / TASK-068 receipt alone ineligible / PL-C and PL-D PASS0 |
| D2.5 SKILL safety | fresh clean-main reimplementation after dirty-hunk owner disposition; canonical correction/release plus installed exact sync and PL-A hash rebind | dirty overlap / partial hunks only / START0 |
| D2.5 SKILL operation authority | config v2 or trusted broker exact-one command redemption plus immutable operation artifact/read-back | missing/N.C. |
| D2.5 SKILL publish confirmation | exact-one stage, TASK-036 import and separate pinned receipt/correlation/canonical/Profile completion | missing/N.C. |
| D2.5 SKILL privacy | independent closed privacy-projection validator completion receipt; fixed `safe_export:true` is ineligible | missing/N.C. |
| D2.5 SKILL strict I/O | strict pinned JSON snapshot/digest equality plus closed Product path/output boundary | missing/N.C. |
| D2.5 SKILL disabled discovery | `D2S-DISABLED-DISCOVERY0`: Draft PR #8 `6a39133` makes the default sentinel `bridge_root:null` and returns disabled status before any Bridge probe/availability projection; Product runner still requires explicit operation config | source-covered only / canonical release-install read-back required / Production linkage PASS0 |
| D2.5 TASK-058 File Bridge | canonical corrective completion/release/install read-back plus downstream baseline rebind | missing/N.C. |
| D2.5 TASK-058 BVP privacy | independent closed BVP admission validator completion receipt; SKILL flag/key-name redaction is ineligible | missing/N.C. |
| D2.5 TASK-067 read modes | `T67-READBACK-PRIMITIVE-USE`: TASK-068 strict pinned immutable read/existing-lock inspection is candidate-only for VERIFIED_READBACK and sealed A2 terminal lookup; TASK-067 retains exact current-coordinate authority | candidate only / no whole-facade PASS / preserved dirty / COMMIT STOP |
| D2.5 TASK-067 write modes | `T67-WRITE-MODES-VIA-T68`: FRESH/PRECOMMIT_RESUME/JOURNAL_RECOVERY require Project manifest and Generic phase generations, marker/anchor transitions and terminal tombstone outside TASK-068; UNAVAILABLE burns before effect and cannot downgrade to read | High N.C. / source effect0 / preserved dirty / COMMIT STOP |
| D2.5 TASK-036 | `T36-PRODUCT-MONTAGE-DISPATCH` plus `T36-CLOSED-ARGV-NEGATIVES`, packaged execution/readback after TASK-061-A/063/D2S/067 | installer ordering only PASS; Montage START0 / missing |
| TASK-065 design | Option B plus PLA-I01-I20, PL65-A06/A07/A08, PLB-I01-I19, PLC-I01-I16, PL65-B00/B03/B04/B05/C01a/C01b and PL-D D01-D12; installer/config/promotion generations are selected only by a trusted exact plan/receipt, with fixed-target overwrite/restore/delete, mutable pointer, scan-highest and auto-cleanup zero | task-local design active / PL-A/B/C/D START0 / source START0 |

No row inherits PASS from another. Shared `task.md`, roadmap, task-index,
current-state or CHANGELOG synchronization waits for its sole-Builder/LOCK
checkpoint. Until every required receipt is current, TASK-065 source/config/
adapter/native/Production effects remain zero while task-local design and
fixture planning continue.

### Post-restart remote-ref read-back

The Owner-authorized restart rebind fetched origin before resuming task-local
work. At that read-back:

- `origin/main` remained
  `35cdf1ad475633dcf035e0616e979b5a8fde0c88`;
- TASK-065 head/upstream were both at this read-back
  `7cabed393879b61ff02261f988efe34b662b0a75`, with the branch 38 commits ahead
  of and zero commits behind origin/main;
- the only open PR whose head/title matched TASK-060/061/063/065/067/068/069
  was TASK-065 Draft PR #467, at the exact TASK-065 head above;
- no TASK-067, TASK-068 or TASK-069 remote implementation branch or open PR
  supplied a completion receipt;
- existing TASK-060/061/063 remote branch names remained historical/candidate
  refs without a current open completion PR and therefore created no PASS; and
- the preserved TASK-067 worktree stayed at origin/main with its three frozen
  dirty file hashes unchanged and no active TASK-065/067 entry in
  `ACTIVE-WORK-LOCKS.json`.

Consequently no dependency cell advances. This read-back confirms only remote
ref/currentness availability; it does not replace the formal owner, overlap,
work-lock, test, Critic/Judge, hosted or installed completion Evidence required
by each row.

## 6. Shared Current State drift and sole-Builder candidate

At this audit base, shared metadata is not aligned with Git/task-local facts:

- `current-state.md` says `Development Candidate: NONE`;
- `task-index.md` still labels TASK-060
  `ALLOCATION_METADATA_PENDING_IMPLEMENTATION_NOT_AUTHORIZED` and TASK-061
  `DEPENDENCY_BLOCKED_IMPLEMENTATION_NOT_AUTHORIZED`;
- TASK-063 and TASK-065 have no aligned active rows in the inspected table; and
- TASK-067 has no canonical task record, task-index row, Current State row,
  Allowed Files or implementation authority.

Candidate source being an ancestor of main is not completion or Production
authority, but shared metadata claiming implementation absence also cannot
authorize a new TASK-067 mutation lane. The preserved TASK-067 diff therefore
remains COMMIT STOP.

A future exact sole-Builder/LOCK checkpoint should reconcile, without
overstating completion:

1. TASK-060/061 as candidate-present with independent/real-E2E completion
   pending;
2. TASK-063 corrections canonical with native installed read-back pending;
3. TASK-065 dependency-gated with separate D0/D1/D2/D2.5 rows;
4. TASK-067 as either explicit COMMIT STOP design candidate or formally
   allocated task with exact owner, Allowed Files and implementation-start
   Gate; and
5. the global Development Candidate value.

TASK-065 does not write these shared files. The list is a candidate handoff,
not a reservation, Lock acquisition or current authority.
