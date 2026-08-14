# TASK-043 — Major Refactor Full Detailed Design

- Baseline: `main@6784a44e6831daa2b3db8ff85e2abe7b197ba3de`
- Scope: TASK-043 foundation plus the contracts consumed by TASK-042 P-V6-4,
  TASK-044 and TASK-045
- Profile: `DEV-4 FOUNDATION CRITICAL`
- Design state: `BUILDER_DRAFT_FOR_CRITIC`

## 1. Problem

BAI VIDEO PRODUCTION stores valid domain truth in multiple independently versioned
JSON/SQLite artifacts. It cannot yet describe one complete reopenable Product
Project, migrate it as a unit, recover an interrupted multi-store save, or provide
generic Undo/Redo, Autosave, Backup and durable Shell jobs. The requested Timeline
Audio and full NLE would otherwise create new state without a safe Project boundary.

## 2. Existing implementation

Reuse, do not replace:

- `SQLiteProductStore` schema migrations and production jobs;
- atomic JSON writes, checksum and CAS in domain stores;
- `ProductionBundleStore`, Planning/Production and Session bundles;
- TASK-037..041 transaction journals and recovery paths;
- `DesktopSessionCheckpointStore` and
  `DesktopEditingApplicationCheckpointStore` for quiescent local checkpoints;
- `ShellApplicationService` command authority and close guard;
- TASK-010 operation identity/idempotency and Native confirmation model.

## 3. Domain model

### ProductProjectManifest

```text
project_format_version
project_id
project_revision
created_at / updated_at
product_version
timebase
child_bindings[]
project_manifest_sha256
```

Each `ChildBinding` has `domain_owner`, `relative_path`, `format_id`,
`format_version`, `content_sha256`, `required`, and optional `dependency_hashes`.
Paths are canonical relative paths below the selected Project root.

### ProjectCommandRecord

Append-only metadata for reversible Product-local commands:
`command_id`, `command_type`, `actor_kind`, `before_revision`, `after_revision`,
`forward_payload_sha256`, `inverse_payload_sha256`, `state`, `created_at`.
Sensitive payloads are referenced, not embedded.

### DurableJobRecord

`job_id`, `operation_identity`, `kind`, `target_identity`, `input_hashes`, `state`,
`attempt`, `created_at`, `updated_at`, `unknown_since`, `recovery_actions`,
`result_ref`, `error_code`. It is the Product job truth used by TASK-044; it does
not replace TASK-027 Generation Queue or Provider Attempt Evidence.

## 4. Schema

New public/package schemas:

- `product-project-manifest.schema.json`
- `project-save-journal.schema.json`
- `project-command-history.schema.json`
- `durable-product-job.schema.json`

Schemas are closed objects, use exact SemVer strings, bound collections and text
lengths, reject absolute/traversal paths and never permit credential fields.

## 5. Versioning

`format_id` and SemVer are separate. Readers advertise exact supported ranges.
Patch/minor additions are not assumed compatible unless a registered reader says
so. A newer unknown version fails with `ERR_PROJECT_FORMAT_NEWER_UNSUPPORTED` and
does not mutate files.

## 6. Migration

Migration registry entries declare `format_id`, `from_version`, `to_version`,
`lossless`, `requires_human_gate`, `planner` and `applier`.

```text
inspect -> plan -> copy to staging -> migrate staging -> validate all children
-> produce diff/Evidence -> atomic manifest switch -> retain pre-migration backup
```

No in-place child rewrite. Unknown, lossy, destructive or external-target
migrations return `READY_FOR_HUMAN_GATE`.

## 7. Backward compatibility

Legacy projects without a Product Manifest are discovered read-only from known
canonical filenames. The importer produces a migration plan; it never guesses
project identity or silently adopts unrelated files. Existing `1.0.0` child
documents remain valid and unchanged.

## 8. Persistence

The Project root contains:

```text
.bai-project/project.json
.bai-project/save-journal.json
.bai-project/history.json
.bai-project/jobs.json
.bai-project/autosave/
.bai-project/backups/
```

All targets are regular non-symlink files beneath the canonical root. Writes use
temporary siblings, fsync where supported, atomic replace and previous-checksum
CAS. A Project-scoped coordinator lock is held from final child-hash validation
through manifest replacement; every binding is re-read immediately before the
manifest is committed last. A changed child aborts without switching the
manifest.

## 9. Application Service

`ProductProjectApplication` exposes read-only `inspect/open/plan_migration`, then
authorized `create/save/apply_migration/restore_backup`. It coordinates existing
domain services; it does not expose their raw mutable registries.

## 10. Command/capability

Shell capabilities are explicit:

- `project.open`, `project.save`, `project.autosave`, `project.backup`;
- `project.migration.preview`, `project.migration.apply`;
- `edit.undo`, `edit.redo`;
- `job.enqueue`, `job.cancel`, `job.reconcile`.

Availability is derived from current state, not merely from a visible button.

## 11. State machine

Project save: `IDLE -> PREPARING -> STAGED -> VALIDATED -> COMMITTING -> COMMITTED`.
Crash/exception produces `RECOVERY_REQUIRED`; invalid input produces `REJECTED`.

Durable jobs:
`QUEUED -> PREFLIGHT -> READY -> DISPATCHING -> RUNNING -> SUCCEEDED|FAILED|CANCELLED|UNKNOWN|HUMAN_REQUIRED`.
`UNKNOWN` never retries automatically.

## 12. Authority

The Manifest is aggregation truth only. Domain data ownership remains with its
existing Task. Project save may persist Product-local state; it cannot authorize
Provider, paid, credential, Resolve/Cubase or Production operations.

## 13. Human Gate

Required for lossy/destructive migration, unknown external state, paid Provider,
new credential entry, ambiguous human-owned Resolve/Cubase target, Production
Deploy and restore that would overwrite a newer human revision.

## 14. Security

Reject symlinks/reparse traversal, absolute paths, `..`, device paths, oversized
JSON, duplicate child identities, checksum mismatch and path case collisions.
Allowlisted Project root is resolved before every write. Private bodies and
secrets never enter manifest/history/job public status.

## 15. Credential

Only opaque Provider profile IDs and versions may be referenced. Credential
material remains OS-backed under TASK-034 and is resolved only at separately
authorized execution time.

## 16. Cost

Project operations are local/free. Job records support `estimated_cost`,
`currency`, `estimate_source` and `actual_cost`, each nullable. `null` means
unknown, never zero. Cost ceilings remain owned by existing Planning/Budget truth.

## 17. Paid/local

TASK-043 implements no paid execution. Local deterministic file operations are
runnable. Cloud/paid operations require their current adapters and gates.

## 18. Provider capability

Project snapshots may bind Provider profile/catalog versions for reproducibility,
but never claim runtime availability. TASK-028/032/033 remain capability truth.

## 19. Prompt model

Only Prompt IDs, versions, hashes and private body references are bound. Prompt
text is excluded from Project manifest, history, jobs, logs and migration Evidence.

## 20. Reference roles

Start/End bindings retain explicit `CHARACTER`, `SPACE` and `COMPOSITION` roles.
Start and End cardinalities remain independent. DIRECT_CONTINUATION references
the exact previous End Asset identity; no visual-similarity substitution.

## 21. Error classification

Use stable prefixes:

- `ERR_PROJECT_FORMAT_*` validation/compatibility;
- `ERR_PROJECT_SAVE_*` state/CAS/journal;
- `ERR_PROJECT_MIGRATION_*` planning/apply/rollback;
- `ERR_PROJECT_HISTORY_*` undo/redo;
- `ERR_PRODUCT_JOB_*` durable job state.

Errors retain Product category, retryability and safe user action without host
paths or secrets.

## 22. Retry

Pure reads and staging writes may use bounded retry on transient sharing errors.
Manifest commit, migration apply and external dispatch are not blindly retried.

## 23. Idempotency

Save identity is `(project_id, from_revision, content_set_sha256)`. Migration
identity adds `(from_version, to_version, plan_sha256)`. Job operation identity
binds kind, target and exact inputs. Same identity returns the existing terminal
or pending record; different input is a conflict.

## 24. Timeout / unknown state

Timeout after a dispatch boundary becomes `UNKNOWN`. Recovery exposes inspect,
reconcile, mark failed or accept externally proven completion as typed actions.
No automatic replay is allowed.

## 25. Recovery

Open checks journal first. Before manifest switch, staged files can be abandoned.
After child staging but before manifest switch, recovery verifies and completes
the same transaction or restores the last manifest. A partial external operation
is never inferred from Product files.

## 26. STALE

When a bound child checksum changes outside the manifest transaction, Project
state is `STALE_CHILD_BINDING`. TASK-037/039 content STALE remains separate and
is projected, not duplicated. Undo that changes an upstream contract runs the
normal dependency STALE propagation.

## 27. Evidence

Record plan hash, before/after manifest hashes, child hash set, migration ID,
validation results, recovery action and actor kind. Evidence excludes absolute
paths, credentials, Prompt bodies and media bytes.

## 28. Observability

Local structured events include correlation ID, operation identity, duration,
state transition, error code and bounded counts. No outbound telemetry is added.

## 29. UI interactions

TASK-043 adds Project open/save/recovery status, Autosave indicator, Backup list,
migration preview and Undo/Redo availability. TASK-044 owns Timeline controls:
generic clip click seeks, candidate click reviews, tracks are dynamic, viewport
supports zoom/Fit/scroll, and trim/snap/IN-OUT dispatch typed commands.

## 30. Accessibility

Every pointer action has a keyboard command and visible focus. Timeline exposes
track/clip/time/state semantics, not color alone. Recovery and migration previews
use headings, lists, live status and explicit confirmation text.

## 31. Performance

Project open loads the manifest and indexes only required child headers first.
Timeline and Asset views virtualize. Acceptance budgets are measured, not claimed:
2h+ Timeline, at least 10,000 clips/cues and a large Asset index fixture. Exact
thresholds are fixed in TASK-045 after native baseline measurement.

## 32. Regression

Compatibility corpus covers current v0.20.1 child stores, legacy no-manifest
projects, corrupt checksums, interrupted journals and newer unknown versions.
Existing domain tests remain mandatory.

## 33. Test matrix

- schema positive/negative and resource parity;
- manifest canonicalization/hash/path security;
- create/open/save/reopen and CAS conflict;
- migration preview/apply/rollback/roundtrip;
- failure injection at every save phase;
- Undo/Redo branching and STALE propagation;
- Autosave debounce/quiescence/retention;
- Backup rotation/restore conflict;
- durable job restart/idempotency/UNKNOWN;
- Shell bridge request validation;
- full repository regression and compile/static checks.

## 34. Native acceptance

TASK-043 native acceptance proves open/save/reopen, crash-recovery prompt,
Autosave/Backup/Undo behavior and path security. TASK-044 adds real Timeline and
Export Queue interaction. TASK-045 repeats clean-profile, multi-monitor/DPI,
Narrator, keyboard and packaged EXE gates. Mock/browser evidence cannot become
`NATIVE_VALIDATED`.

## 35. Rollout

1. Ship readers and Project creation without changing existing child formats.
2. Add save coordinator behind explicit Project open/create.
3. Add history/Autosave/Backup.
4. Add durable jobs.
5. Integrate Timeline Audio and interactive editor.
6. Release only after TASK-045 gates.

## 36. Rollback

Before a release, revert the feature branch/PR. For project data, retain the exact
pre-migration manifest and backup; rollback restores by a new verified transaction.
Never replace published Tags or mutate historical Evidence.

## 37. Release impact

TASK-043 alone is a checkpoint, not a meaningful release. The integrated
user-facing slice is expected to be MINOR while backward compatible. If actual
Project/API compatibility is intentionally broken, SemVer is re-decided from
evidence; no version is precommitted.

## 38. Documentation synchronization

Synchronize Roadmap, Current State, Task Index, TASK-042 status/summary, TASK-043
records, user Project format/migration/recovery guide, README workflow and release
notes. Claims distinguish implemented, hosted, native, parked and planned.

## 39. Exact allowed files

### Roadmap/design unit

- `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md`
- `docs/ai-team/current-state.md`
- `docs/ai-team/task-index.md`
- `docs/ai-team/tasks/TASK-042/task.md`
- `docs/ai-team/tasks/TASK-042/TASK-042.summary.md`
- `docs/ai-team/tasks/TASK-043/**`
- `docs/ai-team/tasks/TASK-044/**`
- `docs/ai-team/tasks/TASK-045/**`
- `PROJECT.md`
- `CHANGELOG.md`

### TASK-043 implementation candidate

- `src/ai_video_production/product_project*.py`
- `src/ai_video_production/project_migration*.py`
- `src/ai_video_production/project_history*.py`
- `src/ai_video_production/durable_product_job*.py`
- matching `src/ai_video_production/schema_resources/*.json`
- matching public `schemas/*.json`
- `src/ai_video_production/__init__.py`
- focused `tests/test_task043_*.py`
- required Task/Evidence/docs files above

Provider adapters, credential storage, media outputs, Resolve/Cubase mutation,
package version, Tag, Release and Deploy are excluded from the first implementation
unit. Any required file outside this list triggers a Critic/Allowed-Files update.

## Implementation order

1. schema contracts and canonical codec;
2. read-only inspector and migration plan;
3. manifest create/open/save with CAS;
4. save journal and failure-injection recovery;
5. compatibility corpus and roundtrip;
6. Undo/Redo command history;
7. Autosave and Backup;
8. durable Product jobs;
9. Shell projection;
10. focused/full/native evidence and closure sync;
11. TASK-042 P-V6-4 implementation re-audit against the accepted Project contract.
