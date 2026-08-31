# TASK-068 verification checkpoint

Status: `PASS / COMMIT_READY`

## Bound source

- Base: `origin/main@35cdf1ad475633dcf035e0616e979b5a8fde0c88`
- Branch: `codex/task-068-secure-authority-io`
- Dedicated worktree: `task-068-secure-authority-io`
- Shared files modified: none

## Executed evidence

- Python syntax compilation under WSL: PASS
- Python syntax compilation on Windows after the latest P0 corrections: PASS
- POSIX focused security/race/fault suite after the resume corrections: `89 passed`; Windows-only collection under WSL: `25 skipped`
- POSIX primitive smoke: `O_TMPFILE` plus live-handle `linkat(AT_EMPTY_PATH)` publishes exactly one final name; no temporary namespace entry: PASS
- Windows direct temporary-directory smoke for initial lock and immutable publish: PASS
- Windows native handle-race smoke: live temp replacement denied, pinned ancestor rename denied, and live cleanup-target replacement denied; foreign files preserved: PASS
- Windows private one-shot capability smoke: no public instance dictionary/reset field, normal reuse rejected with `CAPABILITY_BURNED`: PASS
- Windows durability rollback smoke: initial-lock and immutable-publish first directory-flush failures remove only the exact owned inode, leave no named temp, and return confirmed non-unknown failure: PASS
- Windows inheritance-failure smoke: the fd returned by the native open port is closed before the body-free rejection escapes: PASS
- `IMMUTABLE_ONLY_V1` mutable-CAS discovery: returns `CAS_ATOMIC_UNAVAILABLE` before document traversal/effect, preserves target bytes, leaves zero temp artifacts, and reports `authority_created=false`; former mutable acceptance is `SUPERSEDED`
- `IMMUTABLE_ONLY_V1` cleanup discovery on both platforms: returns `CLEANUP_ATOMIC_UNAVAILABLE` before target/hook/effect, preserves published and foreign artifacts, and reports `authority_created=false`; former physical-delete acceptance is `SUPERSEDED`
- Windows-native focused test functions, executed unchanged through an isolated in-memory dependency-free runner because pytest is not installed: `25 passed`; `0 skipped`; `0 failed`. Each function received a fresh temporary root, every MonkeyPatch stack was reversed, and the current-source SHA-256 remained `A0F37468C35325D976366D504AA480489A0A5F0C9A66686D487FB5FB101FA6CF`.
- Read target-handle close fault: the close is attempted, the document is not returned, and the public result is body-free `HANDLE_CLOSE_FAILED`: PASS
- Windows named-temp open failure after CREATE_NEW: native handle delete plus close removes the exact owned name; cleanup ambiguity returns `HANDLE_CLEANUP_UNKNOWN`: PASS
- POSIX unnamed-temp/ancestor validation close faults return `HANDLE_CLEANUP_UNKNOWN` after all available handle cleanup is attempted: PASS
- Windows raw CREATE_NEW HANDLE abandonment marks the exact owned object delete-pending and closes the native handle before failure escapes: PASS
- POSIX lock-inode migration into a substituted root is rejected before publication; both original and substituted roots have receipt delta zero: PASS
- Windows targeted current-source smoke: basic initial lock/publish, raced final symlink no-redirect, and final-seam hardlink rejection all PASS. The full 25-function Windows-native focused file also PASSed through the dependency-free current-source runner; execution through the pytest package remains unavailable because pytest is absent.
- Independent Tester rebound source SHA-256 `A0F37468C35325D976366D504AA480489A0A5F0C9A66686D487FB5FB101FA6CF`, repeated the WSL result (`89 passed`, `25 skipped`), and executed all 25 Windows-native focused functions through a dependency-free shim: `25 passed`, `0 skipped`, `0 failed`. No install or download occurred.
- Historical independent DEV-4 rereview found Critical/High `0/2` under the superseded mutable-CAS/delete acceptance. The Owner-approved `IMMUTABLE_ONLY_V1` amendment removes those effects from v1 rather than weakening safety; fresh independent closure review is pending.
- Independent architecture rereview confirmed that current Linux/Windows namespace primitives cannot bind replace/delete atomically to an expected target inode under an uncooperative writer. `IMMUTABLE_ONLY_V1` adopts exact-coordinate immutable generation/transition semantics and keeps both unsupported effects fail-closed.
- Current source SHA-256 `EF52D9246770642BD7BC79A43711629F22D22723C89AA2E19B967E5DC5ADBBEE`: independent Tester reran the amended focused suite with `107 passed / 28 Windows-native skipped` under WSL and all 28 Windows-native functions through the dependency-free runner with `28 passed / 0 skipped / 0 failed`; Tester Critical/High is `0/0`.
- Trusted-plan exact-coordinate and integrity negatives PASS: missing/forged/wrong-instance plans, malformed operation/revision/path, body mismatch, raw reserved-namespace bypass, same-body/different-inode binding, collision, unknown artifact, scan race, fork, missing predecessor, orphan, cycle, and cross-operation binding all STOP+preserve without winner/currentness authority.
- Post-Critic corrective focused suite: Python compilation PASS; WSL `123 passed / 45 Windows-native skipped`. Added Windows case-variant/available-short-name namespace rejection, all semantic plan-fingerprint field rebinding, exact aggregate graph verifier, tombstone replay/resume STOP, directory-tree commit unavailable, and mutable-phase advance unavailable. Independent Windows rerun and fresh Critic/Judge are pending; this local PASS does not lift COMMIT STOP.
- Independent Tester for source SHA-256 `CF7BE4EA6475ACD0B5559E84607310F6153213B26D6BCBC94EC6252307B0946B`: WSL `123 passed / 45 skipped / 0 failed`; Windows dependency-free runner `45 PASS / 0 SKIP / 0 FAIL`, including live distinct `IMMUTA~1` alias. Tester C/H `0/0`. This evidence predates the final pinned-parent TOCTOU correction and must be rerun against the final source.
- Final source SHA-256 `839342F33050703EB21321A019EB5579501ED0611268DE65F0CF274B0732973A`: WSL focused `124 PASS / 48 Windows SKIP / 0 FAIL`; independent Windows dependency-free runner `48 PASS / 0 SKIP / 0 FAIL` across 34 functions/48 expanded cases. Direct and nested distinct 8.3 alias paths, both pinned-parent race seams, terminal repeat collision, and all public duplicate-currentness markers PASS. Independent Tester C/H `0/0`.
- Final TASK-058/TASK-068 targeted regression on the same source: `240 passed / 1 skipped`; the sole skip is the unavailable installed SKILL fixture and is not reported as PASS.
- TASK-058 targeted regression with current TASK-068 POSIX suite: `221 passed / 1 skipped` (installed SKILL unavailable); TASK-068 failures zero.
- Repository regression collection: `NOT_CONFIRMED` because the WSL environment lacks `cryptography.hazmat.primitives.kdf.argon2` for 29 unrelated collection targets.
- Collection-compatible repository regression: `4320 passed`, `43 skipped`, `9 failed`; the 9 failures are environment-only (2 indirect Argon2id imports, 7 WSL attempts to execute Windows PowerShell with `Exec format error`). TASK-068 test failures: 0.

## Review state

Owner Design Gate `IMMUTABLE_ONLY_V1` is satisfied. Final independent implementation Critic/Judge and Tester both report Critical/High `0/0` against source SHA-256 `839342F33050703EB21321A019EB5579501ED0611268DE65F0CF274B0732973A`; COMMIT STOP is lifted after final diff/scope check. TASK-069 source start remains prohibited until this completion receipt is merged into canonical main and a fresh TASK-069 Git/ownership gate passes.
