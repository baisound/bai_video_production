# TASK-021 Attention-State Read-Only Bridge R3 Evidence

## Identity and authority

- Active Project: `BAI VIDEO PRODUCTION`
- Task / Atomic Unit: `TASK-021 / ATTENTION-STATE-READ-ONLY-BRIDGE-R3`
- Run identity: `task021-r3-20260922-01a0c6cf`
- DEV profile: `DEV-3 HIGH ASSURANCE`
- Owner continuation instruction: `次へ`
- Worktree: `C:\Users\user\.codex\worktrees\1a51\bai-video-production`
- Branch: `codex/task-021-attention-state-r3`
- Base / starting HEAD: `origin/main@c8af0a6decf03509dc62891dd037b0f4214d8b81`

The base includes TASK-021 R2 through PR `#567`. Its exact pull-request checks were `9 / 9 PASS`; post-merge CI was `6 / 6 PASS` and post-merge Security was `PASS`. Fresh overlap audit found no open TASK-021 pull request.

R3 is a bounded continuation of the existing TASK-021 Dashboard/Operations responsibility. The R0 canonical design already owns Incident and Alert read models and permits a body-free public projection of their state, severity, lifecycle and reason codes. R3 projects only the exact records enumerated by the already-read canonical integrated snapshot. It does not create a new Task, store, Incident, Alert, notification sender, acknowledgement/resolution command, operation owner, authority token or Product runtime dependency.

## Allowed and changed paths

- `src/ai_video_production/task021_operations_dashboard.py`
- `tests/test_task021_operations_dashboard.py`
- `docs/ai-team/tasks/TASK-021/attention-state-read-only-bridge-r3-evidence-2026-09-22.md`

Schemas, canonical TASK-021 record validators/classifiers, source stores, Product shell, workflows, version metadata, `CHANGELOG.md`, BAI Development OS and unrelated worktrees remain unchanged.

## Implementation result

- Added one optional injected attention-state reader carrying exact immutable tuples of existing canonical `DashboardIncidentReadModel` and `DashboardAlertClassificationReceipt` records.
- The reader is called at most once per refresh. Both record-hash sets must exactly match the Incident and Alert hashes in the canonical `IntegratedDashboardSnapshotRevision` already read by the dashboard.
- Any Alert bound to an Incident must reference one of the exact supplied Incident records. Missing snapshot, missing non-empty record set, hash crossing, unbound Alert, wrong wrapper/member type and reader exception all fail closed into public redacted failure rows.
- The Japanese `Incident` and `Alert` sections each expose at most one fixed-identity aggregate row. Multiple records never create per-record rows, ordinals or exact-count text; only the precedence-selected public state, highest active severity and next-step guidance are shown.
- Incident freshness takes precedence over resolution state. `STALE`, `INVALIDATED` and `UNKNOWN` can never be projected as resolved success.
- `ACKNOWLEDGED` remains `確認済み・未解決`; acknowledgement never implies resolution. `RESOLVED_PROVEN` is successful only as the canonical closed lifecycle. `SUPPRESSED_BY_POLICY` means the Alert classification is not a notification target and is not used as an overall health proof.
- Empty Incident/Alert tuples remain `EMPTY` and explicitly state that absence alone is not health proof. Overall health and coverage remain owned by the integrated snapshot section.
- IDs, hashes, timestamps, source coordinates, receipt references, private details and low-count details are omitted. Fixed summary row identifiers do not depend on record identity or cardinality.
- Every rendered row remains `operation_available=False`. The effect surface explicitly keeps Alert acknowledgement/resolution false; dashboard execution, notification send, external app/process control, automatic repair and Production effects remain false.
- Existing callers that omit the optional reader remain source-compatible and retain their prior section set.

## Critic review

The bounded implementation/security review checked exact snapshot membership, cross-Incident Alert binding, stale/invalidated/unknown precedence, ACK-versus-resolution semantics, empty-list health claims, low-count/private identity leakage, reader exception redaction and static effect surfaces.

The independent Critic found two material fail-closed gaps:

1. Per-record rows and ordinal labels disclosed exact low cardinality even though the canonical public projection fixes `low_count_details_included=false`.
   - Correction: replace all non-empty Incident/Alert rows with one fixed-identity, count-free aggregate row per section; add a two-record negative test proving row count, labels and HTML do not reveal cardinality or private identities.
2. The canonical record validator intentionally permits closed enum combinations, so a directly constructed `SUPPRESSED_BY_POLICY` record with a non-INFO severity or Incident binding could have been rendered as success even though `classify_alert` cannot produce it.
   - Correction: validate exact classifier-derived lifecycle/severity/reason/receipt/Incident-binding combinations before projection; any inconsistency fails both attention sections closed. Explicit invalid-suppression tests cover both mismatches.

Coverage also proves that a non-current Incident cannot render resolved success and that both sections fail together on incomplete or crossed canonical membership.

Final unresolved Critical / High / Medium findings: `0 / 0 / 0`.

## Verification

Technical result: `PASS`

- Pre-change focused TASK-021 baseline: `57 passed`
- Final focused TASK-021 canonical + dashboard suite: `69 passed`
- Final direct dependency regression: `158 passed, 1 skipped`
  - Asset registry/store
  - TASK-043 Durable Product Job
  - TASK-044 Interactive Timeline
  - TASK-044 Export Queue
  - TASK-027/037 Production Bundle planning
  - TASK-037/041 Production Bundle validation/store
  - TASK-021 canonical operations contract and Japanese dashboard
- The single skip is the existing Windows exclusion for the POSIX inode swap-back regression.
- Final `compileall`: `PASS`
- Final `git diff --check`: `PASS`
- Static no-filesystem/network/process/store surface: `PASS`
- Source SHA-256: `5FCA83F33FE5F5C2876DB98D9CE45098C8CF8639FE685254389E98EE8523473C`
- Test SHA-256: `9ADB3C37C54D257E7813E2AC461A550DFCD60A618B811C49AC92AA88B8C2EA57`

The first direct dependency run used pytest's unmanaged OS default temporary directory and recorded `90 passed, 1 skipped, 65 setup errors` because that directory was inaccessible. No Product assertion failed. The unchanged regression scope was rerun with `--basetemp` bound to the exact operation-owned root and passed as reported above.

## Output roots and residuals

All task-owned validation output was contained under:

`C:\Users\user\.codex\worktrees\1a51\bai-video-production\.tmp\task021-r3-20260922-01a0c6cf`

The exact root held the validation venv, pytest base directories and compile caches. Its physical containment, exact leaf identity and operation-owned marker were revalidated before recursive removal; `EXISTS_AFTER=False`. Standard shared pip cache entries may remain under the OS-managed pip cache and were not deleted or repurposed.

The mandatory external checkpoint was written to and read back from:

`C:\home\baisound\evidence\bai-video-production\TASK-021\attention-state-read-only-bridge-r3\task021-r3-20260922-01a0c6cf\evidence-checkpoint.json`

Checkpoint SHA-256: `FC89292B7845C284E92501907CE41A274D82429503708030CD946AD40A9FE699`.

External/native/provider/model/audio/private-media operation: `NOT_EXECUTED`.

## Gates and next action

- Dashboard operation, Job/Export execution, Alert acknowledgement/resolution, notification send, automatic repair and external app/process control: not authorized and not performed.
- Release / Deploy / Production Activation: not authorized and not performed.
- Provider/model acquisition or execution, audio, learning, private media and real-media calibration: outside this Atomic Unit.
- Next action: commit the exact three-file scope, then run PR/hosted integration gates against the exact candidate head.
