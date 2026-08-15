# TASK-045 P-RC-1 Implementation and Critic Evidence

Date: 2026-08-15
Authority: `BVP-TASK-045-P-RC-1 / IMPLEMENTATION`
State: `HOSTED_CLOSED`

## Allowed Files amendment 1

The authorized focused regression exposed an existing concurrent Ingest defect:
two committed source-manifest revisions can race between the current-revision
check and the atomic replacement of `source-manifest.json`. The lower revision
can therefore replace the higher derived pointer. This is a Release Closure data
integrity defect and cannot be waived as test timing.

The exact P-RC-1 Allowed Files set is amended before the corrective edit with:

- `src/ai_video_production/atomic.py` -- bounded cross-process update lock;
- `src/ai_video_production/ingest.py` -- serialize current-revision check and
  derived-pointer replacement;
- `tests/test_task003_asset_ingest.py` -- existing regression plus schema v3
  migration-history expectation.

No Ingest authority, Asset identity, versioned manifest, Evidence, paid Provider,
credential, Release or Production Deploy behavior is expanded.

## Amendment Critic review

- Critical: `0`;
- High: `0` unresolved;
- the correction preserves versioned manifests as canonical and changes only the
  derived convenience pointer publication;
- the lock is sibling-path scoped, cross-process on Windows/Linux, and encloses
  only the latest-record query plus bounded atomic JSON replacement;
- a lower committed revision is never allowed to overwrite a higher committed
  pointer after lock acquisition;
- existing failure injection and fail-closed validation stay in force.

Judge decision: `ALLOWED_FILES_AMENDMENT_AUTHORIZED`.

## Implementation checkpoint

- focused compatibility/save/history/Ingest regression: `100 / 100 PASS`;
- schema history is additive and exact: `1 -> 2 -> 3`;
- concurrent source-manifest derived pointer cannot roll back after the bounded
  update lock is acquired;
- Critic follow-up closed an unbounded pre-read risk by checking migration child
  size before `read_bytes()`;
- Final Critic closed ambiguous dependency remapping when duplicate child bytes
  share one checksum but only a subset migrates; automatic apply now fails before
  Backup/write unless the referenced checksum has one exact target;
- 10,000-Asset performance acceptance uses seven samples per page and the median,
  rather than a single timing sample.

## Acceptance Evidence

- explicit legacy no-manifest preview performs no write and apply revalidates the
  exact preview before creating the closed Product manifest;
- registered transformations accept only exact lossless, non-Human-Gate
  transitions and validate deterministic bounded target bytes before Backup;
- migration uses TASK-043 Backup and coordinated save, verifies exact reopen,
  supports verified restore as a new revision, and reuses journal recovery after
  an injected interruption;
- missing transformer, invalid target, stale preview, unsafe symlink, unsupported
  newer format and ambiguous dependency checksum all fail before Project write;
- SQLite schema v3 is additive, preserves migration history `1 -> 2 -> 3`, and
  installs the `(job_id, asset_id)` index;
- 10,000 Assets traverse in stable unique pages of at most 200; first and second
  page seven-sample medians remain within the accepted `500 ms` budget on the
  WSL2-on-Windows test environment;
- concurrent Ingest revisions preserve versioned canonical manifests and cannot
  roll the derived latest pointer backward.

## Validation

- focused compatibility/save/history/Ingest: `100 / 100 PASS` in `12.99 s`;
- full WSL2 regression: `1123 / 1123 PASS` in `45.78 s`;
- WSL2 compileall `src tests`: `PASS`;
- `git diff --check`: `PASS`;
- local Windows Python launcher/runtime was unavailable during P-RC-1; no local
  Windows PASS is retrospectively claimed;
- hosted Windows/Linux CI: PR #75 `9 / 9 PASS`;
- exact PR head: `30b20deb09f26c27ef98b0518953748fdc4c9c0f`;
- exact main merge: `402c8956a5f5f3ac485c43db2b3e35e667846a88`;
- remote branch and dedicated checkout cleanup: `PASS`.

## Final Critic / Judge

- duplicate Project/Asset truth: none;
- arbitrary Project-supplied code execution: impossible; transformers are
  code-registered callables only;
- partial/destructive migration claim: blocked by preflight, Backup, journal,
  exact reopen and recovery Evidence;
- unbounded Asset materialization: excluded from the new Product page API;
- unresolved Critical/High: `0 / 0`.

Judge decision: `P_RC_1_HOSTED_CLOSED`. Exact SemVer, Tag, GitHub Release and
Production Deploy were not performed in P-RC-1.
