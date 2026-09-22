# TASK-021 Canonical Job/Evidence Read-Only Bridge R4 Evidence

## Identity and authority

- Active Project: `BAI VIDEO PRODUCTION`
- Task / Atomic Unit: `TASK-021 / CANONICAL-JOB-EVIDENCE-READ-ONLY-BRIDGE-R4`
- Run identity: `task021-r4-20260922-01a0c6cf`
- DEV profile: `DEV-3 HIGH ASSURANCE`
- Owner continuation instruction: `次へ`
- Worktree: `C:\Users\user\.codex\worktrees\1a51\bai-video-production`
- Branch: `codex/task-021-canonical-read-model-r4`
- Base / starting HEAD: `origin/main@9cfb7b46f9b210af68729e63b14fbc13e62f173d`

The base includes TASK-021 R3 through PR `#568`. Its exact pull-request checks were `9 / 9 PASS`; post-merge CI was `6 / 6 PASS` and post-merge Security was `PASS`. A fresh overlap audit found no open TASK-021 pull request and no active TASK-021 work lock.

R4 is a bounded continuation of the existing TASK-021 Dashboard/Operations responsibility. The R0 canonical design already owns body-free `DashboardJobReadModel` and `DashboardEvidenceReadModel` records. R4 projects only exact records enumerated by the already-read canonical integrated snapshot. It creates no new Job, Evidence truth, queue, store, action, authority token or Product runtime dependency.

## Allowed and changed paths

- `src/ai_video_production/task021_operations_dashboard.py`
- `tests/test_task021_operations_dashboard.py`
- `docs/ai-team/tasks/TASK-021/canonical-job-evidence-read-only-bridge-r4-evidence-2026-09-22.md`

Schemas, canonical TASK-021 record constructors/classifiers, source stores, Product shell, workflows, version metadata, `CHANGELOG.md`, BAI Development OS and unrelated worktrees remain unchanged.

## Implementation result

- Added one optional injected reader carrying exact immutable tuples of existing canonical Job and Evidence read models. The callback is called at most once per refresh.
- Both record-hash sets must exactly equal the Job and Evidence hashes in the canonical `IntegratedDashboardSnapshotRevision`. Every read model must also bind to one of that snapshot's exact source-binding hashes.
- Every supplied snapshot and canonical R2-R4 record is reconstructed through its canonical `from_dict(to_dict())` boundary before use. Direct-constructor corruption, hash tampering, unknown fields, missing fields and malformed private bodies fail closed without exposing exception content.
- Invalid or missing required records fail both new sections closed. A corrupt integrated snapshot also fails its R1 section and all configured R2-R4 dependent sections closed.
- The Japanese `統合Job状態` and `統合Evidence状態` sections each expose at most one fixed-identity aggregate row. Multiple records never create per-record rows, ordinals or exact-count text.
- Freshness is evaluated before result state. `STALE`, `INVALIDATED` and `UNKNOWN` never project a current Job result or current Evidence result.
- Canonical Job state precedence remains fail-closed: failed, Human-required, unknown, cancelled, in-progress and succeeded-only states have distinct public outcomes. No operation can be started from a row.
- Evidence `FAIL` remains failure. `UNKNOWN` and canonical `NOT_SUPPORTED` remain unknown rather than being weakened to a warning. Only current all-`PASS` records project success.
- Empty Job/Evidence tuples remain `EMPTY` and explicitly state that absence alone is not success/PASS proof. Overall health and coverage remain owned by the integrated snapshot section.
- IDs, hashes, timestamps, source coordinates, operation identity, evidence type, artifact references, reason codes, private details and low-count details are omitted.
- Existing callers that omit the optional reader remain source-compatible and retain their prior section set.
- The effect surface remains zero: canonical mutation, Job/Export execution, dashboard operation execution, Alert acknowledgement/resolution, provider/model calls, private-media/audio work, automatic repair, Release and Deploy remain false.

## Critic review

Independent review covered canonical-owner separation, exact snapshot/source membership, record integrity, freshness/result precedence, low-count and private-data disclosure, exception redaction, optional-reader compatibility and the no-effect boundary.

Three material findings were corrected:

1. Directly constructed Job/Evidence record objects could satisfy `isinstance` while carrying corrupt internal data, allowing later dictionary access to raise outside the reader redaction boundary.
   - Correction: reconstruct every received Job/Evidence record through canonical validation and catch the complete validation/hash/membership path. Direct-constructor corruption tests cover both record kinds and private-string redaction.
2. Evidence `NOT_SUPPORTED` was initially projected as a warning even though canonical `build_snapshot()` classifies it as `UNKNOWN`.
   - Correction: align the public section with the canonical unknown result and add a closed-state test.
3. The same direct-constructor corruption path existed in the required integrated snapshot and previously implemented Operation/Attention internal records.
   - Correction: central snapshot reconstruction and dependent fail-closed behavior; reconstruct proposal, confirmation, execution receipt, Incident and Alert records before projection. Negative tests cover corrupt snapshot, proposal, Incident and Alert objects and prove private values are not rendered.

Final unresolved Critical / High / Medium findings: `0 / 0 / 0`.

## Verification

Technical result: `PASS`

- Pre-change focused TASK-021 baseline: `69 passed`
- Final focused TASK-021 canonical + dashboard suite: `91 passed`
- Final direct dependency regression: `180 passed, 1 skipped`
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
- Source SHA-256: `7264DF7AC71359C856D393675A44586206AC53C0D7A3E9F4DF8B6DD730732ED2`
- Test SHA-256: `1A79C1411FC321819EB5F14A4B57080A07D830DB22A71EFCCEA0C438E9FA7EC4`

The first editable-install attempt was blocked by the restricted network before dependency installation. The unchanged repository-declared `.[dev]` install was retried through the approved network boundary and completed. No provider, model, media or Product runtime was invoked.

## Output roots and residuals

All task-owned build and validation output was contained under:

`C:\Users\user\.codex\worktrees\1a51\bai-video-production\.tmp\task021-r4-20260922-01a0c6cf`

The exact root held the validation venv, pytest base directories and compile caches. Its physical containment, exact leaf identity and operation-owned marker were revalidated before recursive removal; `EXISTS_AFTER=False`. Standard shared pip cache entries may remain under the OS-managed pip cache and were not deleted or repurposed.

The mandatory external checkpoint was written to and read back from:

`C:\home\baisound\evidence\bai-video-production\TASK-021\canonical-job-evidence-read-only-bridge-r4\task021-r4-20260922-01a0c6cf\evidence-checkpoint.json`

Checkpoint SHA-256: `7ABB35B55CF99D7B91A5F79BBCAC931250AD92CE942D5BA98E73D8D7D6B3ED9B`.

External/native/provider/model/audio/private-media operation: `NOT_EXECUTED`.

## Gates and next action

- Dashboard operation, Job/Export execution, Alert acknowledgement/resolution, notification send, automatic repair and external app/process control: not authorized and not performed.
- Release / Deploy / Production Activation: not authorized and not performed.
- Provider/model acquisition or execution, audio, learning, private media and real-media calibration: outside this Atomic Unit.
- Next action: commit the exact three-file scope, then run PR/hosted integration gates against the exact candidate head.
