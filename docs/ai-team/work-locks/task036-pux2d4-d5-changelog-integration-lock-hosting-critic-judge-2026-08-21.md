# TASK-036 P-UX-2D4/D5 CHANGELOG Integration Lock hosting Evidence

## A. Outcome and authority

- Unit: `TASK-036/P-UX-2D4-D5-CHANGELOG-INTEGRATION-LH0`.
- Authority: Owner explicit instruction on 2026-08-21 to proceed only after
  all-green, then merge, clean branches/worktree, Tag and Release.
- This transaction hosts governance only. It does not edit `CHANGELOG.md`, the
  target implementation, workflows, version, Tag or Release state.
- Allowed files are exactly this Evidence and
  `docs/ai-team/work-locks/ACTIVE-WORK-LOCKS.json`.

## B. Fresh source and serialization

- Hosting base: `main@e394cead16407d7177419a07a687094350f3b017`.
- Registry transition: revision `24 -> 25`.
- Active Integration Locks before this transaction: `0`.
- Target branch:
  `codex/task-036-pux2d5-final-review-export-queue@f0353c5aa9dbe252609f822c5d7baa6856307786`.
- Target Draft PR: `#187`; hosted test matrix, dependency audit and secret scan
  passed. Its only failure is the unchanged-CHANGELOG release-metadata check.
- Open PR overlap at audit: only target PR #187; overlap with the exact hosting
  files is `0`.

## C. Target implementation invariant

- Target diff against the hosting main contains exactly `18` paths.
- Canonical `git diff --raw --no-abbrev origin/main...target` graph SHA-256:
  `e64b5294f0bf0db435c089f2bc5a099645c2b3220189d52efef535d4b960f259`.
- The graph contains P-UX-2D4 typed Final Review Shell binding, P-UX-2D5 exact
  durable Export Queue admission, TASK-044 Project/restart/runtime-lease
  corrections, UI wiring, tests and Evidence.
- During the later integration effect, all 18 paths and the graph digest must
  remain unchanged. Only `CHANGELOG.md` may be added.

## D. Exact later CHANGELOG effect

The only allowed later line is:

> - Added TASK-036 P-UX-2D4/D5 trusted Final Review handoff from current typed approval through private ExportPreparation to exactly one durable TASK-044 Export Queue Job, with explicit Human confirmation, Project-scoped exclusive admission, restart-safe EXPORT recovery, runtime lease isolation and Shell projection that exposes no host path or dispatch/render authority. P-UX-2E packaged-native output read-back, per-Job dispatch/render, publication, Release and Deploy remain separate Gates.

The target composition must be exactly `18` immutable implementation paths plus
one Integration-owned `CHANGELOG.md` path. No workflow exception, package
version change or other shared-file edit is allowed during this effect.

## E. Ordered workflow

1. Validate this exact two-file transaction, commit, push and open a Draft Lock
   hosting PR.
2. Require every hosted check to finish with `SUCCESS`.
3. Reconcile main, Registry revision, files, head and overlaps; then merge using
   the repository canonical merge method.
4. Read back Registry revision 25 and this exact record from merged main; require
   post-merge CI and Security `SUCCESS`.
5. From that fresh main, perform a normal main-into-target merge. Rebase, force
   and manual conflict resolution are forbidden.
6. Recompute the 18-path raw blob graph; any mismatch stops the effect.
7. Add the approved physical CHANGELOG line in a separate Japanese commit and
   push.
8. Require target PR #187 to contain exactly 19 paths and every hosted check to
   finish with `SUCCESS` before Ready/merge.
9. Read back merged main, close this Lock in separate append-only Evidence, then
   perform authorized cleanup.
10. Version selection, version-file mutation, annotated Tag and GitHub Release
    remain a separate exact release unit after target and Lock closure.

## F. Failure and UNKNOWN policy

- Main, Registry, target head, path or blob drift stops only the shared write.
- There is no automatic rebase, force, reset, revert, workflow exception or
  unchanged-head retry.
- A merge conflict is not manually resolved under this unit.
- A timeout or unobservable GitHub result remains `UNKNOWN` until exact
  read-back.
- Tag and Release are not reported as PASS without an exact non-reused version,
  exact merged-main target and successful publication read-back.

## G. Critic

- High: the target PR was opened before a dedicated Integration Lock and could
  never become all-green. Correction: do not retry the unchanged head; host this
  exact lock first and bind the already-observed failure to one approved line.
- Medium: path count alone would allow same-path blob drift. Correction: bind
  the complete raw blob graph digest and exact target head.
- Medium: Owner Release authority did not select a version. Correction: keep
  version, Tag and Release outside this CHANGELOG effect and require a separate
  exact release unit after target merge and Lock closure.

Residual `C/H/M/L = 0/0/0/0`.

## H. Judge

- Governance scope: `PASS`.
- Exact two-file hosting transaction: `PASS`.
- Target 18-path immutable graph: `PASS`.
- CHANGELOG effect now: `NOT_EXECUTED`.
- Target merge now: `NOT_EXECUTED`.
- Version/Tag/Release now: `NOT_EXECUTED`.
- Residual `C/H/M/L = 0/0/0/0`.
