# TASK-098 A6-R1 CI Compatibility Repair Evidence

- Date: `2026-09-22`
- Run ID: `20260922T223035+0900`
- Project: `BAI VIDEO PRODUCTION`
- Task / Atomic Unit: `TASK-098 / A6-R1 CI compatibility repair`
- Governance: `DEV-3 HIGH ASSURANCE`
- Worktree: `C:\home\baisound\projects\bai-video-production\.worktrees\task-098-universal-wav-review-integration`
- Branch: `codex/task-098-a4-review-workspace`
- Pre-repair HEAD: `0b63eca497a3103e1ab296ad40d840ea0f0f992a`
- Integrated `origin/main`: `ae456f46d0124108740be92a0411b83ce5e1c75b`
- Existing PR: `#562`, remote head `codex/task-098-universal-wav-review-integration`

## Trigger and findings

The existing PR head ended at A2-R2c and was an ancestor of the local A6-R1
branch. Its six hosted test jobs failed. Representative Linux and Windows logs
showed the owner-canonical V6.1.1 identity assertion failing; Windows also
showed two TASK-098 stale-process race failures caused by attempting to pickle
an immutable record backed by `mappingproxy`.

Current `origin/main` was 31 commits ahead of the original base. It merged
without Product-source conflicts; current-state updates were preserved
automatically. No second PR or parallel Task authority was created.

## Repair

1. The deterministic TASK-098 transcription-control and WAV-review HTML
   composition moved from `task036_shell_ui.py` into the canonical V6.1.1
   template path through `task098_shell_html.py`.
2. `task036_shell_ui.HTML` now aliases the exact canonical V6.1.1 object.
3. Immutable runtime-transcription records implement pickle reconstruction by
   calling their validating constructor with `to_dict()` output.
4. A direct adjudication-record pickle regression covers the Windows spawn
   boundary. Existing publication/cancel stale-process races exercise the
   complete process path.

## Verification

- Python compile: `PASS`
- Git diff check: `PASS`
- Isolated canonical HTML composition: `PASS`
- Isolated validating pickle round-trip: `PASS`
- Root-cause tests: `4 PASS`
- V6.1.1 visual contract plus TASK-098 coordination: `98 PASS`
- TASK-036 Shell plus trusted launcher: `115 PASS`
- A6 Shell application/projection/native selection: `14 PASS / 1 SKIP`
- Total non-overlapping bounded regression: `227 PASS / 1 SKIP`
- Skip reason: `BVP_TASK098_PRIVATE_WAV` was not supplied; no second private
  playback was required for this CI-only repair.

The installed Python lacks `jsonschema` and `cryptography`. Process-local
import stubs were used only to make these bounded tests importable; they were
not committed, performed no crypto/schema claim and were removed. Hosted CI
with real dependencies remains `NOT_CONFIRMED` until the branch is published.

## Safety and residuals

- Test roots were unique children of the active worktree and were removed
  after containment revalidation.
- Temporary import-stub directory: removed.
- Intentional residual artifacts: this canonical Evidence and the required
  external checkpoint only.
- Private WAV playback, model/runtime acquisition, Dataset/training,
  TASK-041 completion, package/install, Release, Deploy and Production:
  `NOT_EXECUTED`.
- Remote push: `NOT_EXECUTED`.
- External checkpoint:
  `C:\home\baisound\evidence\bai-video-production\TASK-098\a6-r1-ci-compatibility-repair\20260922T223035+0900\checkpoint.md`
- External checkpoint size / SHA-256:
  `3019 bytes` / `b0249c0df96bbd138ad5982e0541494ac1d0b1da36a2b312fc847b072fcfea10`
- External checkpoint read-back: `PASS`

## Next action

After commit-ready review and external Evidence read-back, publish the exact
local TASK-098 branch to the existing PR #562 only if Git remote-publication
authority is active, then require all hosted checks to pass. A5 remains blocked
on the canonical TASK-047 receipt ABI and a fresh DEV-4 review.
