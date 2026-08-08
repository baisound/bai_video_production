# TASK-001 — Test / Fix History

This file preserves development-time observations rather than rewriting them into the final PASS result.

1. Initial DEV-4 run: `32 passed, 1 failed`. Failure: original external archive `/Users/...` personal-path detection was missing.
2. Scanner correction run: `33 passed`.
3. Implementation Critic added resume and contract tests. A test fixture had a local `store` variable NameError; product code was not the cause.
4. Corrected fixture and checkpoint mismatch test: `35 passed`.
5. Integrity/immutability/profile/job-scope regressions were added during Critic fixes.
6. Final pre-documentation regression after concurrency tests: `43 passed`.
7. Final Evidence regression after documentation rendering: `43 passed in 1.64s`; compileall PASS; wheel build (`--no-build-isolation`) PASS.

Final independent test evidence is recorded in `tester-report.md` and `evidence/test-output-final.txt`.
