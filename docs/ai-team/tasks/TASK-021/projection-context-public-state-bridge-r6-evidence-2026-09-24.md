# TASK-021 Projection Context Public-State Bridge R6 Evidence

## Identity and authority

- Active Project: `BAI VIDEO PRODUCTION`
- Task / Atomic Unit: `TASK-021 / PROJECTION-CONTEXT-PUBLIC-STATE-BRIDGE-R6`
- Run identity: `task021-r6-20260924-01a0c6cf`
- DEV profile: `DEV-3 HIGH ASSURANCE`
- Owner continuation instruction: `次へ`
- Worktree: `C:\Users\user\.codex\worktrees\1a51\bai-video-production\task021-r6-worktree`
- Branch: `codex/task-021-projection-context-public-state-r6`
- Base / starting HEAD: `origin/main@89c38719cc2158eb26d0e3f48cd1e0a0ba645c32`

The base includes TASK-021 R5 through merged PR `#577`. A fresh overlap audit found no open TASK-021 pull request and no existing local or remote R6 branch. During implementation, `origin/main` advanced by three non-overlapping TASK-047 documentation commits. The candidate was rebased onto `origin/main@e6557d99d4333f51dee49b6ddb8d4c03ba5e7428` and fully reverified before hosted review.

R6 is a bounded continuation of the existing TASK-021 Dashboard/Operations responsibility. The R0 canonical design already owns `DashboardProjectionPolicyRevision`, `DashboardQueryIntent`, and their exact digests in `IntegratedDashboardSnapshotRevision`; R6 only bridges those immutable records into the existing Japanese read-only dashboard. It creates no second policy, query, snapshot, store, clock, action, authority token, or Product runtime dependency.

## Allowed and changed paths

- `src/ai_video_production/task021_operations_dashboard.py`
- `tests/test_task021_operations_dashboard.py`
- `docs/ai-team/tasks/TASK-021/projection-context-public-state-bridge-r6-evidence-2026-09-24.md`

Schemas, canonical TASK-021 record constructors and snapshot calculation, policy/query owners, source owners/stores, Product shell, workflows, version metadata, `CHANGELOG.md`, BAI Development OS and unrelated worktrees remain unchanged.

## Implementation result

- Added one optional injected reader carrying the exact immutable canonical projection policy, query and caller-supplied evaluation instant. The callback is called at most once per refresh.
- Both supplied records are reconstructed through their canonical `from_dict(to_dict())` paths before use. Unknown/missing fields, malformed values, digest tampering and direct-constructor corruption fail closed.
- The policy and query digests must exactly match the canonical integrated snapshot. The query project must match the dashboard project, and the query page size must remain within the exact policy.
- Snapshot generation must fall inside the policy's effective interval. A supplied evaluation instant may not predate the snapshot. A policy that has since expired is projected as a warning rather than silently treated as current.
- Snapshot source, combined Job/Evidence, Alert and Incident cardinalities are rechecked against the exact policy caps.
- When the optional R5 source-binding reader is also present, every verified source kind must be selected by the exact query. An invalid source-binding bridge cannot support a successful query-binding claim.
- The Japanese `表示条件` section exposes two fixed-identity rows only: policy currentness and exact snapshot/query binding. It exposes no policy/query/source identifier, digest, authority reference, cursor, timestamp, page size, filter, source kind, sort order, count or body.
- Reader exceptions and malformed private content are redacted. Missing, crossed, corrupt, wrong-project, over-cap, future-policy or back-dated evaluation inputs fail the section closed.
- Existing callers that omit the optional reader remain source-compatible and retain their prior section set.
- The effect surface remains zero: canonical/source mutation, Job/Export execution, dashboard operation execution, Alert acknowledgement/resolution, provider/model calls, private-media/audio work, automatic repair, Release and Deploy remain false.

## Critic and Judge review

The DEV-3 Critic responsibility reviewed canonical-owner separation, exact digest binding, policy interval semantics, caller-supplied evaluation-time monotonicity, query/project and query/policy consistency, all snapshot caps, optional R5 source-kind cross-checking, exception redaction, public low-detail output, optional-reader compatibility and the no-effect boundary.

One implementation hygiene finding was corrected during verification: the first package compilation command emitted ignored bytecode files beside source files. All 479 task-generated files were removed after resolving and checking the exact task worktree path, and compilation was rerun with its cache redirected into the task-owned temporary root. No repository content was deleted.

The Judge gate found the unit bounded to the existing R0 policy/query/display responsibility, with no schema, persistence, execution, wall-clock read or authority expansion. The current-main-integrated candidate is eligible for hosted verification.

Final unresolved Critical / High / Medium findings: `0 / 0 / 0`.

## Verification

Technical result: `PASS`

- Pre-change focused TASK-021 baseline: `101 passed`
- Final dashboard suite: `77 passed`
- Final focused TASK-021 canonical + dashboard suite: `106 passed`
- Final direct dependency regression: `195 passed, 1 skipped`
  - Asset registry/store
  - TASK-043 Durable Product Job
  - TASK-044 Interactive Timeline
  - TASK-044 Export Queue
  - TASK-027/037 Production Bundle planning
  - TASK-037/041 Production Bundle validation/store
  - TASK-021 canonical operations contract and Japanese dashboard
- The single skip is the existing Windows exclusion for the POSIX inode swap-back regression.
- Final redirected-cache `compileall`: `PASS`
- Final `git diff --check`: `PASS`
- Static no-filesystem/network/process/store surface: `PASS`
- Post-rebase focused TASK-021 suite: `106 passed`
- Post-rebase direct dependency regression: `195 passed, 1 skipped`
- Source SHA-256 before commit: `686211C9986F1120069E83CF9A3EA8DD4F5A1CB67E845BF473FDBD47D3BE8F62`
- Test SHA-256 before commit: `CA879BF2ACCB362D0DA913364C828578F41CBB37C9A9E6EF0B0D677CF081D402`

Validation used the task-local Python 3.13.14 environment with the unchanged repository-declared `.[dev]` dependencies. No provider, model, media or Product runtime was invoked.

## Output roots and residuals

All task-owned build and validation output is contained under:

`C:\Users\user\.codex\worktrees\1a51\bai-video-production\task021-r6-worktree\.tmp\task021-r6-20260924-01a0c6cf`

The exact root currently contains the validation environment, pytest base directories and redirected compile cache. It is an intentional residual until hosted closure and final Evidence persistence are complete. Standard shared pip cache entries may remain under the OS-managed pip cache and are not owned for cleanup by this unit.

The mandatory external checkpoint was written to and read back from:

`C:\home\baisound\evidence\bai-video-production\TASK-021\projection-context-public-state-bridge-r6\task021-r6-20260924-01a0c6cf\evidence-checkpoint.json`

Checkpoint SHA-256 before commit: `AE76925BB9F3E05188720325A5D81EBE26334E76F6D54F262C467759168BF528`.

External/native/provider/model/audio/private-media operation: `NOT_EXECUTED`.

## Gates and next action

- Dashboard operation, Job/Export execution, Alert acknowledgement/resolution, notification send, automatic repair and external app/process control: not authorized and not performed.
- Release / Deploy / Production Activation: not authorized and not performed.
- Provider/model acquisition or execution, audio, learning, private media and real-media calibration: outside this Atomic Unit.
- Next action: push the exact candidate, open its pull request, and run hosted gates against that exact head.
