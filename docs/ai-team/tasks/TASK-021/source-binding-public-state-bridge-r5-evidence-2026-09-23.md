# TASK-021 Source Binding Public-State Bridge R5 Evidence

## Identity and authority

- Active Project: `BAI VIDEO PRODUCTION`
- Task / Atomic Unit: `TASK-021 / SOURCE-BINDING-PUBLIC-STATE-BRIDGE-R5`
- Run identity: `task021-r5-20260923-01a0c6cf`
- DEV profile: `DEV-3 HIGH ASSURANCE`
- Owner continuation instruction: `次へ`
- Worktree: `C:\Users\user\.codex\worktrees\1a51\bai-video-production\task021-r5-worktree`
- Branch: `codex/task-021-source-binding-public-state-r5`
- Base / starting HEAD: `origin/main@38fdd6938ab67d33726182b4fba4b8db0134cc6d`

The base includes TASK-021 R4 through merged PR `#570`. A fresh overlap audit found no open TASK-021 pull request and no existing local or remote R5 branch.

R5 is a bounded continuation of the existing TASK-021 Dashboard/Operations responsibility. The R0 canonical design already owns `DashboardSourceBinding` and exact source hashes in `IntegratedDashboardSnapshotRevision`; R5 only bridges those immutable records into the existing Japanese read-only dashboard. It creates no second source registry, source truth, snapshot, store, action, authority token or Product runtime dependency.

## Allowed and changed paths

- `src/ai_video_production/task021_operations_dashboard.py`
- `tests/test_task021_operations_dashboard.py`
- `docs/ai-team/tasks/TASK-021/source-binding-public-state-bridge-r5-evidence-2026-09-23.md`

Schemas, canonical TASK-021 record constructors and snapshot calculation, source owners/stores, Product shell, workflows, version metadata, `CHANGELOG.md`, BAI Development OS and unrelated worktrees remain unchanged.

## Implementation result

- Added one optional injected reader carrying the exact immutable tuple of existing canonical `DashboardSourceBinding` records. The callback is called at most once per refresh.
- Every supplied binding is reconstructed through `DashboardSourceBinding.from_dict(item.to_dict())` before use. Unknown/missing fields, malformed values, record-digest tampering and direct-constructor corruption fail closed.
- The sorted binding digest set must exactly equal the canonical integrated snapshot's `source_binding_hashes`. Missing, empty, extra, crossed or wrong-type values fail the section closed.
- The optional reader requires a valid same-project canonical integrated snapshot. A corrupt or absent snapshot cannot establish a source-binding public state.
- The Japanese `参照元状態` section exposes one fixed-identity aggregate row only. Multiple bindings never create per-source rows, ordinals or exact-count text.
- Closed-state precedence is fail-closed: `MISMATCH` is failure; unresolved or unknown contract states are unknown; bound stale/invalidated freshness or validity is warning; bound unknown freshness or validity is unknown; only all-bound/current/valid records project success.
- The row and accessible HTML omit source kind, source ID/ref/digest/revision/time, binding digests, paths, bodies and low-count details. Reader exception content is redacted.
- Existing callers that omit the optional reader remain source-compatible and retain their prior section set.
- The effect surface remains zero: canonical/source mutation, Job/Export execution, dashboard operation execution, Alert acknowledgement/resolution, provider/model calls, private-media/audio work, automatic repair, Release and Deploy remain false.

## Critic and Judge review

The DEV-3 Critic responsibility reviewed canonical-owner separation, exact snapshot membership, receipt-boundary reconstruction, closed-state precedence, empty/missing semantics, low-count disclosure, exception redaction, optional-reader compatibility and the no-effect boundary.

One material test-design finding was corrected: an initial negative test attempted to construct a zero-source `IntegratedDashboardSnapshotRevision`, but the canonical contract rejects such snapshots. The test and implementation boundary were aligned so an enabled source-binding reader treats `None` and an empty tuple as failure rather than inventing an impossible successful empty state.

The Judge gate found the unit bounded to the existing R0 source-binding/display responsibility, with no schema, persistence, execution or authority expansion. The candidate is eligible for commit and hosted verification.

Final unresolved Critical / High / Medium findings: `0 / 0 / 0`.

## Verification

Technical result: `PASS`

- Pre-change focused TASK-021 baseline: `91 passed`
- Final focused TASK-021 canonical + dashboard suite: `101 passed`
- Final direct dependency regression: `190 passed, 1 skipped`
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
- Source SHA-256: `AE6933C6C5304BFA0D9DDC151B2FE3E21E1A06CAE250C326AA0B637BD80197DA`
- Test SHA-256: `99BB9FD143C7CC5E0533B85513D0095B8E3DE255F5C2876FC03C8F8F328EB93C`

The first system-Python baseline lacked the repository-declared `jsonschema` dependency. The first isolated venv was then found to reference an unavailable Python 3.12 installation outside the execution boundary. A second task-local venv was explicitly bound to the available Python 3.13.14 runtime, received the unchanged repository-declared `.[dev]` dependencies, and produced the final results above. No provider, model, media or Product runtime was invoked.

## Output roots and residuals

All task-owned build and validation output is contained under:

`C:\Users\user\.codex\worktrees\1a51\bai-video-production\task021-r5-worktree\.tmp\task021-r5-20260923-01a0c6cf`

The exact root currently contains the validation environments, pytest base directories and compile cache. It is an intentional residual until hosted closure and final Evidence persistence are complete. Standard shared pip cache entries may remain under the OS-managed pip cache and are not owned for cleanup by this unit.

The mandatory external checkpoint was written to and read back from:

`C:\home\baisound\evidence\bai-video-production\TASK-021\source-binding-public-state-bridge-r5\task021-r5-20260923-01a0c6cf\evidence-checkpoint.json`

Checkpoint SHA-256: `9FB95D6A06986B3E23E0DB13CA8FA1222BD32EA557B6BDCB3D918186C6D88927`.

External/native/provider/model/audio/private-media operation: `NOT_EXECUTED`.

## Gates and next action

- Dashboard operation, Job/Export execution, Alert acknowledgement/resolution, notification send, automatic repair and external app/process control: not authorized and not performed.
- Release / Deploy / Production Activation: not authorized and not performed.
- Provider/model acquisition or execution, audio, learning, private media and real-media calibration: outside this Atomic Unit.
- Next action: commit the exact three-file scope, then run PR/hosted integration gates against the exact candidate head.
