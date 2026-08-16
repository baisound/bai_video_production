# TASK-047 P-OBS dev.10 CHANGELOG Integration Lock hosting Evidence

## A. Outcome and authority

- Unit: `TASK-047/P-OBS-DEV10-CHANGELOG-INTEGRATION-LH0`.
- Authority: Owner standing autonomous TASK-047 lane plus the standing
  release-metadata prevention rule.
- This transaction hosts governance only. It does not edit `CHANGELOG.md`, the
  target implementation, workflows, OBS, audio or Release state.
- Allowed files are exactly this Evidence and
  `docs/ai-team/work-locks/ACTIVE-WORK-LOCKS.json`.

## B. Fresh source and serialization

- Hosting base: `main@92e277c16e51e446dd1e3dd2f701fbaf02f8cd34`.
- Registry transition: revision `19 -> 20`.
- Active implementation Locks before this transaction: P-VS-3B and
  `BVP-LOCK-TASK047-POBS-DEV10-UX-RUNTIME`.
- Active Integration Locks before this transaction: `0`.
- Target branch:
  `codex/task-047-dev10-runtime-controller@aa3b94c826d28d3c4691ccc66806392861eefb0d`.
- Target Draft PR is deliberately not opened before this Lock is hosted, so the
  known `changelog-and-version` blocker is not triggered on a stale five-minute
  retry cycle. The canonical Lock remains bound to the exact branch and head.
- Open PR overlap at audit: `0`; path overlap with the exact hosting files: `0`.

## C. Target implementation invariant

- Target diff against the hosting main contains exactly `45` paths reserved by
  `BVP-LOCK-TASK047-POBS-DEV10-UX-RUNTIME`.
- Canonical `git diff --raw --no-abbrev origin/main...target` graph SHA-256:
  `799dee555f8cb33e1458678154b308d0bb59d1a189da8c0143d5da3d522e732a`.
- The graph covers reviewable Plugin/Controller source, packaging assets,
  installer, tests, Japanese/English guides and body-free Evidence. It contains
  no Owner audio, private recording destination or private audio digest.
- During the later integration effect, all 45 paths and the graph digest must
  remain unchanged. Only `CHANGELOG.md` may be added.

## D. Exact later CHANGELOG effect

The only allowed later line is:

> - Added TASK-047 P-OBS dev.10 reviewable Plugin source and a beginner-friendly Windows Controller/installer for OBS 32.2.1 with selectable recording destination, live Peak/RMS gain meter, persistent recording/paused banners and same-process start/pause/resume/stop. Owner-voice technical Acceptance passed with gap/HMAC/reconnect zero; Dataset adoption, Training, Production use and stable Release remain separate.

The target composition must be exactly `45` immutable implementation paths plus
one Integration-owned `CHANGELOG.md` path. No workflow exception, README rewrite,
package rebuild or extra shared-file edit is allowed during the effect.

## E. Ordered workflow

1. Validate this exact two-file transaction, commit, push and open a Draft Lock
   hosting PR.
2. Require every hosted check to finish with `SUCCESS`.
3. Reconcile main, Registry revision, files, head and overlaps; then use the
   repository canonical merge method.
4. Read back Registry revision 20 and the exact ACTIVE record from merged main;
   require post-merge CI and Security `SUCCESS`.
5. From that fresh main, perform a normal main-into-target merge. Rebase, force
   and manual conflict resolution are forbidden.
6. Recompute the 45-path raw blob graph; any mismatch stops the effect.
7. Add the approved physical CHANGELOG line in a separate Japanese commit, push,
   then open the target Draft PR.
8. Require the target diff to be exactly 46 paths and all hosted checks to be
   terminal `SUCCESS` before Ready/merge.
9. Read back the merged main, publish and independently read back the unsigned
   Technical Preview assets, then close both Locks in a separate append-only H2.

## F. Failure and UNKNOWN policy

- Main, Registry, target head, path or blob drift stops only the shared write;
  there is no automatic rebase, retry, force, reset, revert or rollback.
- A merge conflict is not resolved manually under this unit.
- A timeout or unobservable result remains `UNKNOWN` until exact read/reconcile.
- An actual contradictory Registry/head/file graph is a hard mismatch.
- Failed publication cannot be reported as Release PASS. Product stable Release,
  Dataset, Training and Production remain separate.

## G. Critic self-pass 1

Initial High: opening the implementation PR before reserving CHANGELOG would
repeat the known CI blocker. Correction: host this exact Lock first and keep the
target PR unopened until post-merge read-back.

Initial Medium: a path count alone would not prevent same-path blob drift.
Correction: bind the complete raw blob graph digest and exact target head.

Residual Critical/High/Medium: `0 / 0 / 0`.

## H. Critic self-pass 2

- Registry and Evidence are the only changed paths.
- Registry revision and audit base move together; other root fields and Lock
  records remain byte-semantically unchanged.
- Target implementation and public artifacts are not modified by this unit.
- CHANGELOG, workflow, OBS, audio, Dataset, Training and Production effects are
  not inferred.
- Owner audio identity, path and digest are absent.

Residual Critical/High/Medium: `0 / 0 / 0`.

## I. Judge

- Governance scope: `PASS`.
- Exact two-file hosting transaction: `PASS`.
- Target 45-path immutable graph: `PASS`.
- CHANGELOG effect now: `NOT_EXECUTED`.
- Implementation PR merge now: `NOT_EXECUTED`.
- Public Technical Preview now: `NOT_EXECUTED`.
- Critical/High/Medium: `0 / 0 / 0`.
