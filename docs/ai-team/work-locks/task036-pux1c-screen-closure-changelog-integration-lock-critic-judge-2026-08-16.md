# TASK-036 / P-UX-1C screen closure CHANGELOG Integration Lock — 2026-08-16

## Authority and effect boundary

- Authority source: Owner standing AUTONOMY directives in the current thread.
- Unit: `TASK-036/P-UX-1C SCREEN CLOSURE CHANGELOG LOCK HOSTING H0`.
- Hosting effect: exact governance two-file transaction only.
- Later integration effect: only after this Lock is merged to `main`, read back
  exactly and re-audited against the unchanged target head.
- Target Ready / merge: not authorized by this Lock; packaged native and Human
  gates remain open.
- Provider, paid API, Credential, external NLE, native GUI action, Release and
  Deploy: not authorized.

This transaction records a narrow shared-file Lock. It does not edit
`CHANGELOG.md`, PR #111 implementation/Evidence, workflows or any external
state.

## Fresh source of truth

- Repository: `baisound/bai_video_production`.
- Fresh `origin/main`: `404476acbf8397bd33af1ee9fd6655e6669d23b5`.
- Registry before hosting: revision `12`, state `ACTIVE`.
- Active Integration Locks before hosting: `0`.
- Target PR: `#111`, OPEN / Draft / MERGEABLE.
- Target branch: `codex/task-036-pux1c-screen-closure-r0`.
- Target base/head:
  `404476acbf8397bd33af1ee9fd6655e6669d23b5` /
  `a351e01e3f1b9644c962c04d4de175fd0c962705`.
- Target changed paths: exact `25`.
- Other open PR: #112, exact TASK-047 task/manual paths; overlap with the H0
  two paths and the target 25 paths is `0`.
- Active regular Lock overlap with the H0 two paths: `0`.
- Remote hosting branch collision at creation: `0`.

The existing PR #111 worktree and all unknown user work remain untouched. H0
uses an isolated worktree based on the exact fetched main SHA.

## Exact hosting transaction

Only these paths change:

1. `docs/ai-team/work-locks/ACTIVE-WORK-LOCKS.json`
2. `docs/ai-team/work-locks/task036-pux1c-screen-closure-changelog-integration-lock-critic-judge-2026-08-16.md`

Registry delta:

- revision `12` -> `13`;
- audit base -> exact fresh main above;
- append one ACTIVE Integration Lock bound to PR #111, its exact target head,
  25 immutable Product/Evidence paths and one later allowed file,
  `CHANGELOG.md`;
- roadmap, regular Locks and merge order unchanged.

## Canonical CHANGELOG entry

The only permitted later `CHANGELOG.md` delta is this exact line:

> - Improved TASK-036 P-UX-1C V6.1.1 desktop Shell by connecting existing typed Product snapshots and bounded actions for Planning, Scene and Timeline browsing, WORLD LOCK, Continuity, generation safety and Queue admission, generated-output adoption, Audio placement, Asset/Cut/Final Review, interactive editing, Export recovery and persisted Quick Intent projection. Provider, paid, Credential, external NLE, blanket Export, final Human authority, packaged native visual parity, Release and Deploy remain separate or unclaimed.

H0 records but does not write that line.

## Immutable target binding

The exact target baseline is
`a351e01e3f1b9644c962c04d4de175fd0c962705`. The later integration must retain
the following 25 Git blobs exactly:

| Path | Git blob |
|---|---|
| `docs/ai-team/tasks/TASK-036/p-ux-1c-asset-review-screen-closure-design-critic-evidence-2026-08-16.md` | `f73fabe2635bef5a7d4f181bd1f7850560a01055` |
| `docs/ai-team/tasks/TASK-036/p-ux-1c-assets-candidate-index-projection-2026-08-16.md` | `cda1540bd40b73396d1250bec40ca7cd1fdd9952` |
| `docs/ai-team/tasks/TASK-036/p-ux-1c-audio-workspace-closure-2026-08-16.md` | `88454e791d3b0d6e9db212bd22fd712669da46d5` |
| `docs/ai-team/tasks/TASK-036/p-ux-1c-audit-recovery-closure-2026-08-16.md` | `ce726236d7dbb553f75abe3df6bb3d16d19a83d6` |
| `docs/ai-team/tasks/TASK-036/p-ux-1c-cut-review-candidate-selection-closure-2026-08-16.md` | `1c5af3cf2bf38a41b7b31af2999bcdd52baa54cd` |
| `docs/ai-team/tasks/TASK-036/p-ux-1c-edit-source-inspector-closure-2026-08-16.md` | `a3cbf2798c8feaf4459c3d4680af7ac169d4173d` |
| `docs/ai-team/tasks/TASK-036/p-ux-1c-export-execute-all-safety-closure-2026-08-16.md` | `a3a2549017b0cf3236607a7a4dd89528852424e7` |
| `docs/ai-team/tasks/TASK-036/p-ux-1c-export-job-projection-correction-2026-08-16.md` | `cd671732b59b6722f04a8fb1181e3c360e765587` |
| `docs/ai-team/tasks/TASK-036/p-ux-1c-final-review-aggregate-projection-2026-08-16.md` | `890506cb94097d77abaa11585f34caabbc5f0e88` |
| `docs/ai-team/tasks/TASK-036/p-ux-1c-generation-output-adoption-closure-2026-08-16.md` | `f639de2da351b05d66ce433245a2cb9b119075b8` |
| `docs/ai-team/tasks/TASK-036/p-ux-1c-generation-queue-admission-closure-2026-08-16.md` | `13e82e77c31bbad4c99a8635b5ec5aaa4049d027` |
| `docs/ai-team/tasks/TASK-036/p-ux-1c-home-project-open-action-closure-2026-08-16.md` | `4c9a59bee9de9ba2e1327fa65b33adad8c55c2cf` |
| `docs/ai-team/tasks/TASK-036/p-ux-1c-planning-screen-closure-design-critic-evidence-2026-08-16.md` | `03a1374c4e14cbcf67b05e637b7ff04381d744fb` |
| `docs/ai-team/tasks/TASK-036/p-ux-1c-prompt-evidence-closure-2026-08-16.md` | `3943d191aa5bf9556a1122ace96a3280fac70440` |
| `docs/ai-team/tasks/TASK-036/p-ux-1c-quick-intent-projection-closure-2026-08-16.md` | `e109eb6cb9330cb298304576e8cbd0d0a498d2dd` |
| `docs/ai-team/tasks/TASK-036/p-ux-1c-scene-design-continuity-closure-2026-08-16.md` | `ed7a4ddac157bf6f73aba908b52222870f08cf24` |
| `docs/ai-team/tasks/TASK-036/p-ux-1c-scenes-screen-closure-design-critic-evidence-2026-08-16.md` | `c784723a83b42e7479ec7dc0aac84ec5681945de` |
| `docs/ai-team/tasks/TASK-036/p-ux-1c-screen-closure-autonomous-checkpoint-2026-08-16.md` | `2bd798aa3579ac5e44a8899868a097d586dc38a6` |
| `docs/ai-team/tasks/TASK-036/p-ux-1c-start-end-feasibility-closure-2026-08-16.md` | `639ea96dad1a5ef22419f599e1b6735e26fbb528` |
| `docs/ai-team/tasks/TASK-036/p-ux-1c-world-lock-registry-projection-2026-08-16.md` | `921857b526383e4a3a8621a177d665e465624e36` |
| `src/ai_video_production/task036_shell_ui.py` | `26305c117bf9a6998f2be37af2c854098cc1bba4` |
| `src/ai_video_production/task036_shell_v611.py` | `547fdd72b2e6cc4c0bd19c565bf563039d782c63` |
| `src/ai_video_production/task036_trusted_launcher.py` | `5bb2a2c38c9de3107f2934bf91ad702b077c7496` |
| `tests/test_task036_shell_ui.py` | `fcd458006b72772d4cf2aaab85ccfe32a35f79ee` |
| `tests/test_task036_v611_visual_contract.py` | `d90af2bd7172326931d06a8c1ee055f66c8d9608` |

Any blob drift, different target head, 27th PR path or non-exact CHANGELOG line
expires the integration effect and parks only the shared write.

## Sequencing and invalidation

1. Commit and push the exact H0 two-file diff, then open a Draft PR.
2. Require every hosted H0 check to reach terminal success.
3. Merge H0 through the protected PR path; direct main push is prohibited.
4. Fetch and read the ACTIVE Lock back from exact merged main; require
   post-merge CI/Security success.
5. Re-audit target PR #111 head, 25 blobs, open-PR path overlap and main.
6. Merge fresh main normally into the target branch. Rebase, reset and force
   push are prohibited.
7. Add the one exact approved CHANGELOG line and no other target mutation.
8. Re-run local/hosted checks and preserve the exact 25 implementation blobs.
9. Keep PR #111 Draft and unmerged while packaged native/Human gates remain.
10. Release the Lock only through a later append-only Registry closure after
    the integration effect is complete or the target closes.

Main, target-head, path, check, blob or policy drift invalidates the current
step. No automatic retry, rollback, revert or workflow weakening is allowed.

## Builder Critic

- H0 owns two governance paths only and has zero overlap with PR #112.
- The target Lock owns one later shared file only; the 25 Product/Evidence
  blobs remain under the existing TASK-036 Lock.
- The CHANGELOG sentence describes only completed screen closures and
  explicitly withholds packaged native parity, Human final authority and
  release claims.
- Counts/digests do not replace the exact target path/blob table.

Residual Critical / High / Medium: `0 / 0 / 0`.

## Security / Completeness Critic

- No Provider, paid, Credential, external application, native GUI, Release or
  Deploy effect is introduced.
- No `.github/**` exception or CI weakening is permitted.
- A stale target head, blob drift, overlap or UNKNOWN fails closed.
- The Lock is not effective until merged-main exact read-back.

Residual Critical / High / Medium: `0 / 0 / 0`.

## Provisional Judge

- Exact H0 two-file scope: `PASS`.
- Fresh main, Registry revision and active-lock count: `PASS`.
- Target PR/head/25-blob binding: `PASS`.
- Proposed one-line CHANGELOG scope: `PASS`.
- H0 ready for Japanese commit, normal push and Draft PR: `PASS`.
- Integration Lock effective on main: `PENDING_HOST_PR_MERGE_AND_READ_BACK`.
- Target CHANGELOG mutation: `PENDING_EFFECTIVE_LOCK_AND_FRESH_AUDIT`.
- PR #111 Ready/merge or native parity claim: `NOT_AUTHORIZED`.

Residual design Critical / High / Medium: `0 / 0 / 0`.
