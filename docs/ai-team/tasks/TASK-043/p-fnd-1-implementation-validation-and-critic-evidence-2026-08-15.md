# TASK-043 — P-FND-1 Implementation, Validation and Critic Evidence

- Implementation baseline: `main@b7500fa4f7cb4339ddde6aa4800d56c9bcb4d94e`
- Unit: `P-FND-1 Project Manifest / compatibility / read-only migration plan`
- Provider/paid/native/media/external mutation: `false / false / false / false / false`
- Package/version/Tag/Release/Deploy: unchanged

## Implemented

- closed, hashed `ProductProjectManifest` and packaged/public JSON Schema;
- canonical Project-relative child bindings with Task owner, format version,
  exact file checksum, required flag and dependency hashes;
- reserved control-directory, absolute/drive/traversal/backslash/case-collision,
  symlink and authority-escalation rejection;
- atomic Project Manifest persistence with cross-process lock, first-revision rule,
  exact CAS, immutable Project identity and exact +1 revision;
- supported-format range inspection with required/optional missing, checksum drift,
  newer version, unknown format and migration-required states;
- bounded streaming child checksum calculation;
- deterministic read-only migration registry/path/plan with explicit lossless and
  Human-Gate flags;
- stable hashes for manifest, compatibility report and migration plan;
- public package exports and focused tests.

Migration apply is intentionally absent. The plan always records
`store_write_authorized=false` and `migration_apply_authorized=false`.

## Focused validation

- WSL2 Python 3.12 `compileall src tests`: PASS.
- packaged/public Schema byte parity: PASS.
- Draft 2020-12 schema validation and representative manifest validation: PASS.
- create -> atomic save -> load equality: PASS.
- exact child checksum compatibility: PASS.
- legacy 1.0.0 -> registered lossless 2.0.0 read-only plan: PASS.
- public API import was later blocked by an intermittent WSL service access error;
  the same imports passed in the preceding compile/smoke process. This is not
  recorded as an additional PASS.
- Local pytest is unavailable because WSL has no pytest and sudo requires a
  password. No host package was installed. Full pytest/compile/security remains
  `HOSTED_PENDING` for the PR.

## Implementation Critic Round 1

1. `HIGH / CLOSED` — child binding could point into `.bai-project` and recursively
   bind control truth. Reserved control-directory paths are now rejected by code,
   Schema and test.
2. `HIGH / CLOSED` — required old formats were initially reported readable while
   migration was required. `MIGRATION_REQUIRED` now blocks Product read-only open
   while still permitting a read-only migration plan.
3. `HIGH / CLOSED` — unknown/newer Project Manifest versions could collapse into a
   generic invalid error. Stable newer/migration-required errors now fail closed
   before current-version parsing.
4. `MEDIUM / CLOSED` — file checksum originally read the full child into memory.
   It now streams 1 MiB chunks for large child stores.
5. `MEDIUM / CLOSED` — report/plan hashes were produced but not self-verified.
   Frozen records now validate their deterministic hashes.
6. `MEDIUM / CLOSED` — lexical timestamp comparison could misorder valid ISO forms.
   timestamps are parsed as UTC datetimes before comparison.

## Final Judge

P-FND-1 is `LOCAL_SMOKE_PASS / HOSTED_PENDING`. Unresolved Critical/High is
`0 / 0`. The unit may be published to a PR. It must not be called hosted-closed
until all repository checks pass and exact main merge/cleanup is verified.
P-FND-2 save journal/recovery remains not started.

