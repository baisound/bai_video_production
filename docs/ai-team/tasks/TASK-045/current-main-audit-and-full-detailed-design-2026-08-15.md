# TASK-045 — Current-main Audit and Full Detailed Design

## 1. Problem

The V6 Product Project, Timeline Audio, interactive Timeline/Edit History,
durable Export Queue and Unified NLE Shell are now on `main`, but the formal
release is still `v0.20.1`. The repository must prove old-project compatibility,
copy-on-write migration, recovery, long-project performance, packaged Windows
behavior and clean installation before any broader release claim.

The current documents also lag the actual hosted state: PR #72 is merged, while
several status surfaces still describe TASK-044 P-NLE-4 as hosted-pending and
TASK-045 as dependency-waiting. TASK-045 begins by correcting that drift.

## 2. Current implementation and Source of Truth

- Checkout: fresh clone from `origin/main`
- Design branch: `refactor/task-045-release-closure-design`
- Exact baseline/main: `6703c42a3aa06a563071f1a48dc7aab113f4dfe4`
- Worktree at audit start: clean
- PR #72: `MERGED`, exact merge SHA above, hosted checks `9 / 9 PASS`
- Package version: `0.20.1`
- Latest annotated Tag/formal GitHub Release: `v0.20.1`
- Protected unknown WIP under `D:/BAI/bvp-task042-p-v6-4-autonomy` remains
  outside this checkout and untouched.

Current checkout and GitHub are newer than the pre-merge status documents and
are the implementation Source of Truth.

### Reusable, already implemented

- closed Product Project Manifest with exact child checksums and CAS revisions;
- supported-format inspection and deterministic read-only migration planning;
- child-first/manifest-last save journal with COMPLETE/ROLLBACK/FINALIZE;
- append-only Undo/Redo, Autosave, verified Backup and CAS-safe restore;
- durable Product Job/Export Queue restart-to-UNKNOWN behavior;
- frame-authoritative Timeline, 10,000-clip bounded projection and edit history;
- existing TASK-036 packaged Shell, native picker, keyboard/accessibility and
  multi-monitor acceptance foundations;
- Windows build batch and ignored `builds/` output.

### Missing or partial

1. Migration transitions describe versions but have no executable, typed byte
   transformer and no copy-on-write apply coordinator.
2. The designed read-only discovery path for legacy projects without a Product
   Manifest is absent.
3. There is no checked-in old-project compatibility corpus that proves import,
   apply, reopen, backup restore and rollback as one round trip.
4. Large Timeline projection is bounded and fast, but no TASK-045 gate records a
   two-hour timebase budget together with a large Asset Library query budget.
5. `SQLiteProductStore.list_assets` is unbounded; a 10,000-Asset UI consumer
   would materialize the complete library instead of using a stable page.
6. TASK-045 clean-install, conversation-free restart and final packaged native
   matrix have not run on the integrated post-v0.20.1 code.
7. Exact SemVer, release metadata, tag target and Release notes are undecided.

Existing focused compatibility/recovery/NLE baseline on WSL2 is `94 / 94 PASS`.
The 10,000-clip Shell controller test completed in approximately `0.14 s` on the
current checkout; this is a baseline measurement, not final native performance
Evidence.

## 3. Domain model

TASK-045 adds no second Project or Timeline truth. It adds bounded release-closure
contracts around existing owners:

- `LegacyProjectCandidate`: explicitly supplied project identity plus a closed
  set of discovered canonical child bindings; discovery itself is read-only.
- `MigrationTransformer`: exact `(format_id, from_version, to_version)` code
  identity that transforms canonical bytes without filesystem access.
- `MigrationApplication`: plan checksum, source manifest checksum, pre-migration
  backup identity, resulting manifest checksum and per-child before/after hashes.
- `AssetPage`: stable keyset page ordered by `asset_id`, bounded items and an
  opaque next cursor; it is a query projection, not a new Asset store.
- `ReleaseAcceptanceRecord`: immutable summary of exact commits, test/native
  gates, known limitations and the final version decision.

## 4. Schema

- Add a closed migration-application Evidence schema only if a durable Product
  record is required by implementation; fields must exclude host paths, content,
  credentials and confirmation tokens.
- Test corpus JSON is closed, UTF-8 and contains synthetic/non-sensitive values.
- `AssetPage` is a Python application/query contract; it does not change the
  existing SQLite schema unless measured query evidence proves an index is needed.
- Release Evidence is Product documentation, not runtime authority.

## 5. Versioning

- Current Product Project format remains `1.0.0` unless implementation proves a
  format change is required.
- Migration transformer identity is exact; minor/patch compatibility is never
  inferred.
- Existing child bytes that are already readable remain unchanged.
- Package SemVer remains `0.20.1` during design and acceptance work.
- A backward-compatible, completed user-facing V6 feature set is expected to be
  a MINOR candidate, but `0.21.0` is not selected until P-RC-2 Evidence passes.

## 6. Migration

The only autonomously applicable path is exact, registered and lossless:

```text
load exact manifest
-> inspect exact child bytes
-> create and verify retained backup
-> bind exact migration plan hash
-> transform each child in memory/staging
-> validate target bytes and target format
-> coordinated child-first/manifest-last CAS save
-> reopen and re-inspect
-> persist path-free Evidence
```

No transformer may access the network, invoke a Provider, mutate an NLE or write
outside the Product Project coordinator. Lossy, destructive, ambiguous identity,
unsupported or external-target migration remains `READY_FOR_HUMAN_GATE`.

## 7. Backward compatibility

- Exact v0.20.1 current Project manifests remain readable without rewrite.
- A legacy no-manifest project is discovered only from an explicit closed rule
  set and caller-supplied project identity/timebase; unrelated files are ignored.
- Discovery produces preview/Evidence first and never silently adopts files.
- A new manifest may be installed only in a synthetic/sandbox fixture during
  automated/native acceptance or after an explicit Product migration action.
- Unknown format IDs, invalid SemVer, malformed JSON, newer required children,
  checksum drift, symlinks and path escapes fail closed without mutation.

## 8. Persistence

- Reuse `ProductProjectSaveCoordinator` for staged atomic publication.
- Reuse `ProductProjectBackupStore` for retained pre-migration backup and restore
  as a new Project revision.
- Never overwrite the only copy of a source child.
- Migration Evidence is written after successful reopen; an interrupted save is
  governed by the existing journal and does not claim migration completion.
- Asset paging is read-only and uses the existing SQLite connection/ownership.

## 9. Application Service

`ProductProjectMigrationApplication` composes inspector, planner, transformer
registry, backup and save coordinator. Its public operations are:

- `discover_legacy(...)` — read-only;
- `prepare_apply(...)` — read-only, exact hashes and allowed transition list;
- `apply_lossless(...)` — local Project mutation with one-shot exact confirmation;
- `reopen_verify(...)` — read-only;
- `prepare_restore(...)` / existing restore — explicit CAS-bound recovery.

No generic callable/plugin is accepted through a public UI/CLI boundary.

## 10. Command and capability

- `project.compatibility.inspect`: `READ_ONLY`
- `project.legacy.discover`: `READ_ONLY`
- `project.migration.prepare`: `READ_ONLY`
- `project.migration.apply_lossless`: `HUMAN_FINAL_AUTHORITY` at the Product
  interaction boundary; automated tests use only owned synthetic fixtures.
- `project.backup.restore`: existing `HUMAN_FINAL_AUTHORITY`
- `asset.library.page`: `READ_ONLY`
- Release/Tag: conditionally Owner-authorized only after all required gates.

## 11. State machine

```text
INSPECTED
  -> NO_MIGRATION_REQUIRED
  -> READY_FOR_COPY_ON_WRITE_APPLY
  -> READY_FOR_HUMAN_GATE
  -> BLOCKED

READY_FOR_COPY_ON_WRITE_APPLY
  -> APPLYING
  -> REOPEN_VERIFIED
  -> RECOVERY_REQUIRED
```

`REOPEN_VERIFIED` requires exact target hashes and compatibility PASS. A crash or
unknown commit point never becomes success by timeout.

## 12. Authority

TASK-043 retains Project/save/history/backup ownership. TASK-001/003 retain Asset
truth. TASK-044 retains Timeline/Edit/Export composition. TASK-045 owns only the
compatibility/native/release acceptance and the minimal missing closure code.

## 13. Human Gate

Park only the affected operation for:

- lossy/destructive/ambiguous migration;
- real human-owned Project migration without exact target confirmation;
- unknown external Export state;
- Production Deploy, paid Provider, credential input or destructive external
  operation.

Release/annotated Tag/GitHub Release is already conditionally authorized by the
Owner Directive and is not a separate prompt after all gates pass.

## 14. Security

- root and children must be regular, contained, non-symlink paths;
- manifest/plan/confirmation/source hashes are revalidated immediately before
  mutation;
- migration bytes and Asset results have explicit size/count bounds;
- no archive extraction, arbitrary module loading or executable migration input;
- no host paths, private prompt/media content or credentials in public Evidence.

## 15. Credential

No new credential is accepted, stored or read. GitHub authentication already
configured for repository workflow is used only for the authorized PR/Release
flow. Any new Provider credential path remains a Human Gate.

## 16. Cost

All implementation and acceptance routes are local/free. No paid Provider call,
credit purchase or auto-top-up change is permitted. Context Cost is recorded at
atomic checkpoints where supported; unavailable provider/billed fields stay null.

## 17. Paid/local

Migration, paging, tests, build and packaged native acceptance are local. TASK-013
native H3 replay and TASK-014 paid narration are not TASK-045 requirements.

## 18. Provider capability

No Provider capability changes. Configured routes never imply execution authority.

## 19. Prompt model

No Prompt body/model change. Prompt metadata remains private and checksum-bound.

## 20. Reference roles

No WORLD LOCK/reference-role change. Migration must preserve child bytes and their
existing ownership/identity unless an exact registered transformer states the
lossless target representation.

## 21. Error classification

- `ERR_PROJECT_MIGRATION_*`: stale plan, missing transformer, invalid output,
  apply conflict and reopen mismatch;
- `ERR_PROJECT_LEGACY_*`: ambiguous/missing/unsafe discovery;
- existing `ERR_PROJECT_FORMAT_*`, save/recovery and backup errors are reused;
- Asset cursor/limit validation is `VALIDATION`; SQLite/data corruption remains
  `DATA_INTEGRITY`; time budget failure is acceptance failure, not data loss.

## 22. Retry

Read-only inspection and paging may be retried. Migration apply, restore and any
external Export dispatch are never blindly retried. Retry after known rollback
must re-run inspection and create a new exact confirmation.

## 23. Idempotency

The migration application identity derives from source manifest hash, plan hash,
registered transformer identities and target versions. Repeating after a proven
successful reopen returns the accepted result; it does not create another write.

## 24. Timeout / unknown state

Local timeout/interruption checks the save journal. If commit identity cannot be
proven, state is `RECOVERY_REQUIRED`. External UNKNOWN behavior remains the
TASK-043/044 per-job Human reconciliation route with no automatic replay.

## 25. Recovery

- pre-manifest interruption: COMPLETE or ROLLBACK through the existing journal;
- post-manifest interruption: FINALIZE/reopen verify only;
- migration rollback: restore verified pre-migration backup as a new revision;
- corrupted backup: reject, never substitute current files;
- release workflow failure: do not move/recreate Tag; diagnose at exact SHA.

## 26. STALE

Any source manifest/child checksum change invalidates inspection, plan and
confirmation. Asset page cursors are stable keyset cursors but do not promise a
snapshot across concurrent inserts. Timeline/Edit/Export STALE rules remain owned
by TASK-044.

## 27. Evidence

Record exact baseline/head/merge/tag identities, corpus cases, before/after hashes,
backup/restore results, focused/full test counts, performance measurements,
Windows packaged/native observations, clean-install/restart results and explicit
unavailable/parked gates. Never broaden mock/browser Evidence to native PASS.

## 28. Observability

Expose bounded state, error code, operation identity, elapsed milliseconds and
counts. Do not log media/prompt content, credentials, arbitrary paths or raw UI
automation dumps containing private data.

## 29. UI interactions

TASK-045 validates rather than redesigns the accepted Shell. If migration UI is
needed, it must show source/target version, backup identity, affected child count,
lossless status and exact confirmation; it must not offer blanket migration or
Export execution.

## 30. Accessibility

Keyboard parity, visible focus, semantic control name/state, Narrator/UIA discovery,
narrow/high-scale scrolling and normal focus restoration are required. Color is
never the only state signal.

## 31. Performance

Measure before fixing thresholds. Initial gates:

- 2h+ Timeline with at least 10,000 clips: projection page <= 500 clips and
  median controller projection <= 500 ms on the accepted local test runtime;
- 10,000-Asset library: page <= 200 rows, stable keyset cursor, first/next-page
  median <= 500 ms after fixture creation; full materialization is prohibited in
  the user-facing query;
- native Shell remains responsive during page/zoom/scroll interaction.

Thresholds are acceptance budgets for the tested environment, not universal
hardware guarantees. Any relaxed threshold requires new measured Evidence and
Critic review.

## 32. Regression

Existing domain tests remain mandatory. Add compatibility corpus, migration
apply/rollback/reopen, malformed/newer/corrupt no-write, Asset paging and release
metadata tests. Run focused Windows/WSL2 where available, full WSL2 and Windows,
compileall, package build, clean install and GitHub matrix CI.

## 33. Test matrix

- current v0.20.1 manifest open without rewrite;
- explicit legacy no-manifest discovery and deterministic preview;
- exact lossless single/multi-step migration apply/reopen/idempotency;
- stale plan/confirmation and missing/wrong transformer;
- injected crash before/after child and manifest publication;
- pre-migration backup preview/restore as new revision;
- corrupt/unknown/newer/symlink/path escape fail closed with byte-for-byte no-write;
- 2h/10,000-clip projection and 10,000-Asset keyset paging;
- keyboard/Narrator/UIA/native picker/multi-monitor/high-scale/narrow window;
- per-job READY/UNKNOWN Export safe cancel/reconcile, no Execute All;
- wheel/build/clean install/conversation-free restart/full regression.

## 34. Native acceptance

Use the packaged Windows EXE and owned synthetic Project only. Prove open/reopen,
keyboard Timeline actions, native picker cancellation/success where safe, semantic
UIA/Narrator names, multiple displays/high-scale/narrow layout, long Timeline page
interactions and per-job Export recovery. Browser adapter failure is recorded as
UNAVAILABLE and cannot block an independent safe native gate or become PASS.

## 35. Rollout

### P-RC-1 — Compatibility, migration and performance contracts

Implement explicit legacy discovery, registered lossless migration apply, corpus,
backup/restore roundtrip and bounded Asset paging. Complete focused/full tests,
Evidence, PR, hosted merge, cleanup and fresh-main restart.

### P-RC-2 — Integrated native and installation acceptance

Run/repair only evidence-backed compatibility, long-project, packaged Windows,
clean-install and conversation-free restart gates. Produce a release-readiness
record and exact SemVer decision. Complete PR/hosted merge/cleanup.

### P-RC-3 — Release finalization

From fresh exact main, create `release/<exact-version>`, update all version and
release metadata, run full regression/build/install, open PR, wait for all hosted
checks, merge to main, verify exact merge SHA, create/push annotated Tag, then run
the repository GitHub Release workflow and verify published assets.

## 36. Rollback

Code/document checkpoints revert through a new PR before release. Project data
rollback uses the retained verified backup as a new revision. A published Tag is
never moved or overwritten. GitHub Release notes are corrected only without
claiming unproven capability; Production Deploy never follows automatically.

## 37. Release impact

The integrated post-v0.20.1 feature set is substantial and backward-compatible if
P-RC-1/2 pass, so MINOR is the expected decision class. Exact version remains
`UNDECIDED` until compatibility, native and clean-install Evidence close. Release
notes must separate implemented, native-validated, hosted-validated, parked and
planned scope.

## 38. Documentation synchronization

Synchronize `PROJECT.md`, Project Summary, Current State, Task Index, canonical
Roadmap, TASK-044 closure, TASK-045 state/Evidence, README installation/migration
instructions, CHANGELOG and final Release notes. Historical Evidence is append-only.

## 39. Exact allowed files

### Design unit

- `PROJECT.md`
- `CHANGELOG.md`
- `docs/ai-team/current-state.md`
- `docs/ai-team/project-summary.md`
- `docs/ai-team/task-index.md`
- `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md`
- `docs/ai-team/tasks/TASK-044/task.md`
- `docs/ai-team/tasks/TASK-044/TASK-044.summary.md`
- `docs/ai-team/tasks/TASK-045/**`

### P-RC-1 candidate

- bounded `src/ai_video_production/project_migration.py`,
  `product_project*.py`, `project_save.py`, `project_history.py`, `store.py`,
  `__init__.py`
- new bounded `project_migration_application.py` only if composition cannot stay
  cohesive in the existing migration module
- matching schema resource only if a durable Product record is introduced
- `tests/test_task045_*.py` and synthetic `tests/fixtures/task045/**`
- TASK-045 Evidence and bounded status/roadmap/changelog synchronization

### P-RC-2 candidate

- existing build/native gate scripts under `tools/windows/**`,
  `build-windows-exe.bat`, `packaging/**`, Shell/launcher sources only when an
  observed acceptance failure requires a bounded fix
- TASK-045 tests, Evidence, README/docs and status/roadmap synchronization

### P-RC-3 candidate

- `pyproject.toml`, `src/ai_video_production/__init__.py`, explicit Product
  version constants, `CITATION.cff`, `CHANGELOG.md`, README/version docs,
  TASK-045 Release Evidence and exact status/roadmap surfaces
- `.github/workflows/**` only if an observed release-workflow defect requires a
  separately reviewed bounded corrective

Any file outside the exact active unit requires an Allowed Files amendment and
Critic review before editing.

## 40. Implementation order and exit

The design checkpoint must be hosted-closed first. Then each P-RC unit starts
from fresh exact main on a dedicated branch. TASK-045 closes only when P-RC-1 and
P-RC-2 gates pass and P-RC-3 publishes an exact annotated Tag and verified GitHub
Release. Production Deploy remains blocked. After release, AUTONOMY re-audits
fresh main and continues to the next authorized roadmap milestone.
