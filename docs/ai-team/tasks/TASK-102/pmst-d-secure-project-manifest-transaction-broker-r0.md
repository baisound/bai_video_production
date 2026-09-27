# TASK-102 PMST-D — Secure Project Manifest Transaction Broker R0

Status: `DESIGN_R1_ACCEPTED / PMST_D1_NEXT / SOURCE_NATIVE_NOT_AUTHORIZED`

## 1. Bound decision

The Product keeps `.bai-project/project.json` as its sole canonical Project selector. A Product-local Windows service with a dedicated service SID is the candidate exclusive mutation owner for an enrolled Project control directory. TASK-102 supplies the generic transaction mechanism and migration boundary; it never decides TASK-099 currentness, TASK-076 Job state, TASK-003 Asset state or any caller's semantic transition.

The Owner accepted this architecture and Task allocation in direct response to the 2026-09-27 Human Gate. The acceptance authorizes this design/inventory unit only. Windows feasibility remains `NOT_CONFIRMED`. No service install, account creation, ACL/owner change, directory enrollment, manifest/index/child write, native test, Release, Deploy or Production effect is authorized.

## 2. Canonical boundaries

- TASK-043 remains the historical owner of `ProductProjectManifest`, `ProjectChildBinding` and the canonical pathname. TASK-102 consumes those exact parsers and invariants; it does not change format `1.0.0` in this unit.
- TASK-102 owns enrollment, authenticated private IPC, protected namespace/open-handle barriers, exact predecessor-CAS, operation-bound non-selector witnesses, outcome query and migration of all manifest mutation/recovery routes. Because the chosen ACL boundary protects the whole `.bai-project` directory, TASK-102 also owns the narrowly allowlisted transport/locking mechanism for other protected control objects; it does not own their domain semantics.
- Caller owners construct and validate their successor manifest and retain Job, history, backup, VoiceProfile, Timeline-recovery, child and participant semantics. The broker rejects unauthorized transitions but does not invent them or offer an arbitrary-path/file-write API.
- TASK-068 owns immutable publication/readback. Its `.immutable-authority` topology and receipt must be admitted independently when a manifest selects one of its generations.
- TASK-099 owns JCV-N validation, index semantics and public currentness projection. It consumes TASK-102's generic exact transaction primitive.
- Existing `.bai-project/save-journal.json`, lock/stage files and Project recovery are part of the migration problem because service-only protection of `.bai-project` would otherwise block or bypass them. Protecting only `project.json` while leaving a second user-writable commit journal is not an accepted enrollment.

## 3. Source-derived current writer inventory

The inventory is bound to worktree HEAD `ad4afbbbab4cab243b93060356cc0592d0b1d08b`. It distinguishes semantic entrypoints from the two central pathname mutation sinks.

### Central mutation and recovery sinks

| Route | Current source | Current behavior | Required disposition before enrollment |
|---|---|---|---|
| direct create/replace | `product_project_store.py` `ProductProjectManifestStore.save/_save_unlocked` | cooperative `.project.json.lock`, pathname reread, `AtomicJsonWriter` replacement | public mutation becomes unavailable for enrolled roots; exact broker adapter only |
| coordinated save | `project_save.py` `ProductProjectSaveCoordinator.save/_save_locked` | user-process journal, child stages/backups, final `_save_unlocked` | redesign as one broker-admitted transaction while preserving child participant semantics |
| complete recovery | `ProductProjectSaveCoordinator.recover_complete` | may write journal/children/final manifest | broker-owned recovery or exact broker continuation; no direct final write |
| rollback/reconciliation | `recover_rollback`, participant/orphan reconciliation | mutates child/journal state under cooperative lock | migrate or deterministically block; cannot run beside protected enrollment |

`_save_unlocked` is package-private but is still a bypass surface until all import/call paths and future source-policy checks prevent its use on enrolled roots. A source grep alone does not exclude old installed binaries, plugins or external same-user processes; enrollment must enforce the runtime boundary.

### Observed semantic writer entrypoints

| Owner/application route | Current call shape | Migration class |
|---|---|---|
| TASK-036 trusted launcher bootstrap | direct `ProductProjectManifestStore.save` for revision 1 | broker create-if-absent with exact Project identity |
| legacy Project import in `project_migration_application.py` | direct `save` for initial imported manifest | explicit import transaction; no combined ACL/enrollment migration |
| Project format migration | `ProductProjectSaveCoordinator.save` | coordinated child/manifest transaction |
| Audio Placement | injected `ProductProjectSaveCoordinator.save` | coordinated transaction |
| Interactive Timeline | coordinator save plus complete/rollback recovery | coordinated transaction and recovery |
| Timeline Audio | coordinator save | coordinated transaction |
| Project History restore | coordinator save | restore semantic owner remains TASK-043 history; broker commits exact successor only |
| TASK-048 meter policy | coordinator save with policy child | coordinated transaction |
| TASK-029 montage-learning canonical admission | coordinator save, participant, orphan and complete recovery routes | participant transaction; must preserve external-anchor and recovery semantics |

Read-only users of `ProductProjectManifestStore.load/path` remain readers unless a later inventory proves an indirect writer. `project_history.py` also writes backup copies named `project.json` below history directories; those copies are not the canonical selector and must remain explicitly classified as backup artifacts, never admitted as a broker target.

### Other protected-directory mutation and lock routes

Service-only protection applies to the directory, not just the manifest filename. The following current routes are therefore mandatory migration inputs even when they never change `project.json`:

| Protected object/route | Current source/semantic owner | Required D1 disposition |
|---|---|---|
| `.bai-project/jobs.json` and `.project.json.lock` used by `DurableProductJobStore` | `durable_product_job.py`; Job semantics remain TASK-076 | closed broker object operation or semantic-owner redesign; otherwise enrolled Projects disable Job mutation |
| `.bai-project/history.json` and Project lock used by `ProjectCommandHistoryStore` | `project_history.py`; command-history semantics remain TASK-043 | closed broker object operation and CAS/readback, or explicit unsupported-blocked |
| `.bai-project/autosave/**` and `.bai-project/backups/**` create/replace/rotation/delete | `ProductProjectAutosaveCoordinator` / `ProductProjectBackupStore`; snapshot/backup semantics remain their current owner | broker-mediated bounded directory operation or feature unavailable for enrolled roots; no broad delete capability |
| `.bai-project/voice-profile-revisions.json` and sibling update lock | `voice_profile_store.py`; VoiceProfile semantics remain TASK-046 | closed append/CAS operation or enrolled-root feature blocked pending TASK-046 migration |
| `.bai-project/save-journal.json`, internal stages/backups and lock | `project_save.py` | subsumed by the single accepted broker journal/participant protocol; never dual-run |
| `.bai-project/timeline-edit-command-recovery.json` and internal timeline recovery artifacts | `interactive_timeline_application.py`; Timeline/recovery semantics remain TASK-044 | versioned participant/recovery operation or explicit blocked state |
| Project-lock acquisition without manifest write | `planning_application.py`, `creative_generation_execution_application.py`, `generation_output_adoption_application.py` | replace lock-file mutation with an authenticated broker read lease/snapshot, or mark the affected operation unavailable |
| additional Product lock users | montage-learning transaction paths and any source using `_exclusive_project_lock` or sibling lock helpers | replace with broker lease/participant primitive; no user-created lock inside the protected directory |

This table is a minimum observed set, not an exhaustive claim. Protecting `.bai-project` while granting ad-hoc user exceptions for any row would invalidate the exclusive-writer model. TASK-102 may provide closed object-specific transport primitives, but TASK-076/TASK-043/TASK-046/TASK-044 and other callers keep schema, transition and recovery ownership.

### Required inventory completion before source allocation

PMST-D1 must turn both tables into a machine-checked physical control-directory mutation graph and migration matrix. Discovery must cover `.bai-project` literals, `_manifest_path(...).with_name`, `ProductProjectManifestStore.path(...).with_name`, dynamic descendants, atomic writers, create/replace/rename/unlink/rmdir/rotation helpers, sibling lock helpers, imports/aliases, tests/CLI/installer/recovery utilities, packaged entrypoints, prior supported Product versions and plugin boundaries. Each row must end in `BROKER_MANIFEST_TRANSACTION`, `BROKER_OBJECT_OPERATION`, `BROKER_READ_LEASE`, `READ_ONLY_COMPATIBILITY`, `SEMANTIC_OWNER_REDESIGN_REQUIRED`, or `UNSUPPORTED_BLOCKED`; `UNKNOWN` prevents enrollment. New direct store, protected-object or protected-lock mutations must fail a source-policy test.

## 4. Enrolled security topology

The accepted JCV-N-D R1 conditions are inherited as hard floors:

- `.bai-project` uses a protected non-inheriting DACL and service-owned mutation authority; the ordinary Product/user retains only admitted read/traverse rights.
- the service holds identity-pinned root/control handles without delete sharing and proves no incompatible pre-enrollment mutation handle remains;
- startup and every operation revalidate physical ancestor/control/manifest identity, volume, owner/DACL and enrollment commitments;
- same-logon-user peers, stale handles, parent `DELETE_CHILD`, rename/swap, ACL reassignment, pipe squatting, PID reuse and capability replay are negative cases;
- administrator/backup-privilege takeover, kernel compromise and injection into an admitted worker are outside the live guarantee and force fail-closed recovery;
- an opaque registration maps to a private canonical root; requests never carry arbitrary host paths;
- authenticated pipe endpoints pin process instance, configured identity/build and broker instance; a connection-local one-operation capability is consumed before callbacks.

Every protected-object IPC operation uses a closed operation kind, fixed broker-derived relative target, exact schema/owner/version policy, size/count bounds, predecessor identity/digest and operation-specific transition validator. A generic relative path, arbitrary bytes, caller-selected delete/rename or reusable directory capability is prohibited.

Enrollment is never combined with import, format migration, writer migration or semantic manifest transition. It is available only after the migration matrix is complete and the exact current manifest/control state passes preflight. Service downtime or security drift makes the Project read-only/recovery-required; it never re-enables legacy direct writes.

## 5. Generic transaction and witness boundary

The generic request binds registration, caller/operation kind, exact prior canonical bytes digest and physical identity, exact successor canonical bytes/digest, caller semantic authorization digest, child/participant plan digest where present, broker/enrollment/build epochs, expiry and request digest. The broker reparses both manifests with the TASK-043 parser and enforces identity, revision+1 and caller-specific admitted policy before effects.

A service-owned non-selector witness is durably written `PREPARED` before the commit seam and terminalized as `COMMITTED_DURABLE`, `NOT_COMMITTED_PROVEN` or `UNKNOWN_QUARANTINED`. No later manifest transaction is admitted until the prior witness is terminal and durable. Startup reconciles nonterminal witnesses under reacquired barriers; ambiguous state quarantines the root. Witnesses prove same-operation outcomes after a later successor without becoming a current-head selector.

The existing coordinated save protocol cannot simply continue writing `.bai-project/save-journal.json` as the interactive user. PMST-D1 must choose one exact model:

1. move the full canonical coordinator journal/manifest commit state machine behind the broker while callers retain bounded child preparation; or
2. define a broker-owned generic manifest transaction journal plus strictly versioned participant protocol that subsumes the existing final-manifest/recovery seam.

It must preserve current recovery/participant invariants and prohibit a split-brain pair of old user journal plus new service witness. Child files outside `.bai-project` remain owned by their callers, but the broker must revalidate their exact admitted receipt/identity immediately before and after manifest selection. A mutable or unproved child cannot be selected merely because its hash was supplied.

The same D1 decision must specify how non-manifest protected objects are serialized relative to manifest transactions and recovery. Job/history/profile/autosave/backup/timeline operations cannot silently share the manifest witness or revision coordinate, and TASK-102 cannot reinterpret their records. Each receives a separate closed operation policy and outcome receipt, or the feature is unavailable on an enrolled root until its semantic owner supplies an accepted adapter.

## 6. Windows feasibility gate

PMST-N1 must select and document concrete Windows APIs, access/share flags, handle lifetime, NTFS/version support, replacement failure states, file flush, namespace/directory durability and power-loss claims. `ReplaceFileW` plus the unsupported `REPLACEFILE_WRITE_THROUGH` flag is not assumed sufficient. A documented partial failure that can remove the canonical name is not classified as atomic old-or-new.

Required proof families include:

- incompatible handle present before enrollment; long-lived stale writer; root/control/manifest rename/delete and ancestor swap;
- owner/DACL reassignment and inherited-rights drift; unsupported/reparse/network/cloud/removable topology;
- same-SID foreign client, pipe squat, wrong service/image/build, PID reuse, copied/early/replayed capability and restart;
- predecessor ABA, two admitted writers, exact successor/current/superseded query;
- process kill before/inside/after replacement, service restart, OS crash/power-loss as distinct cases;
- PREPARED/terminal witness crash seams, missing/corrupt witness, later successor and monotonic outcome knowledge;
- coordinator child/participant failure at every journal/commit seam, every listed protected-object/lock route, and old-version writer rejection;
- TASK-068 immutable publish collision/receipt loss/index identity swap and selection refusal.

If the exact target platform cannot prove predecessor exclusion, old-or-new namespace behavior and required durability, the native port is unavailable. Design acceptance must not be reported as native PASS.

## 7. Migration and compatibility order

1. accept D0 responsibility/inventory;
2. freeze D1 protocol, journal/witness model and migration matrix with pure schemas/fault fixtures;
3. implement I1 fake service/client state machine only;
4. execute separately authorized N1 feasibility in an OS-unique contained root;
5. migrate central store/coordinator and each semantic writer/recovery route behind feature-disabled composition;
6. prove old/unmigrated packaged clients cannot mutate an enrolled root and provide deterministic read-only/recovery UX;
7. only then allow enrollment and TASK-099 JCV-N integration.

There is no partial enrollment, dual writer, auto-repair, automatic ACL takeover, destructive cleanup or silent fallback to the legacy lock/store. Existing Projects remain unenrolled and use current behavior until a separately authorized Product migration gate; the presence of TASK-102 source alone changes nothing.

## 8. D0 acceptance boundary

D0 is accepted after one bounded correction cycle. Initial Critic/Judge was `ACCEPT` with C/H/M/L `0/0/0/0`; initial Tester was `REVISE` with `0/1/0/0` for omitted non-manifest protected-directory mutations. R1 added those routes and the complete physical mutation-graph requirement. R1 Critic/Judge and Tester both returned `ACCEPT`, C/H/M/L `0/0/0/0`.

Acceptance covers the responsibility split, inventory classes, security floor, generic coordinator/witness decision requirement, native proof matrix and migration order. It authorizes D1 design only. It does not authorize source, service, ACL, enrollment, native QA, Project writes, private media/model handling, Release, Deploy or Production.
