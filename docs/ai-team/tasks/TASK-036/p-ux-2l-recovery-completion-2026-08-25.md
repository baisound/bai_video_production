# P-UX-2L Recovery Completion

Date: 2026-08-25
Task: TASK-036 / P-UX-2L
Governance: DEV-3 HIGH ASSURANCE
State: TECHNICAL GO / COMMIT-READY

## Repository checkpoint

- Branch: `codex/task-036-pux2l-subtitle-cut-controls`
- Fresh-main validated code HEAD before this completion record: `d8dd6043a53ba587a00931cb172ebf18979bfa82`
- Reviewed feature HEAD: `f9287200f2f8c6633fc31fb6b07ed9a4325d44f1`
- Integrated `origin/main`: `47e176559c358375126af194bde37a008707444d`
- Fresh-main merge: `d8dd6043a53ba587a00931cb172ebf18979bfa82`
- Later TASK-029 R3 lock-closure main integrated: `origin/main` `797feb073cf50d3a440b070265e2dbed7fc59cad`; merge `31dcae0d68ed4cf4f09d9309c4c0c41b235d704e`
- Post-closure Registry read-back: revision 68, nonclosed integration locks 0
- Reviewed implementation/recovery scope: 14 approved files; this completion adds one Evidence file; CHANGELOG and shared Registry excluded
- Worktree: clean before this completion record
- Original TASK-029 worktree and user-owned untracked `tmp/`: not read, staged, modified, or deleted
- Push / PR / merge to main: not performed

## Recovery closure

The previous post-CAS fallible publication boundary is removed.

- `Task036PreEditRuntime.generate_cut_candidates()` constructs and validates the application and optional workflow runtime before the final coordinator CAS.
- The promotion path contains no publisher callback and no launcher-side runtime cache.
- After a successful CAS, only direct in-process application/runtime reference assignments remain.
- Factory failure, wrong application identity, or CAS drift publishes neither the application nor the promoted workflow runtime and preserves exact retry eligibility.
- The trusted Export dispatcher reads the exact workflow runtime held by the bridge and rejects missing runtime or application identity mismatch before dispatch.
- Optional Subtitle first-Cut behavior, repeat-Cut rejection, shared context locking, trusted-launch lifetime, privacy-safe bridge envelopes, and TASK-056 speech-cue compatibility remain intact.

## Verification evidence

- Local fresh-main directly impacted regression: 205 passed across twelve test files.
- Newly integrated TASK-029 R3 focused regression: 8 passed.
- Independent Tester regression: 222 passed.
- Direct trusted-launch Export fixture verifies:
  1. exact promoted runtime receives one dispatch with the exact job, preparation, and destination;
  2. missing runtime fails closed with `ERR_TASK036_WORKFLOW_RUNTIME_IDENTITY` and no dispatch;
  3. application identity mismatch fails closed before the foreign dispatcher can run.
- Python compile/AST checks for the eight modified Product modules: PASS.
- Embedded JavaScript `node --check` and Node behavior checks: PASS.
- `git diff --check`: PASS.
- Fresh-main target-path drift: none.
- Provider, paid service, model download, Resolve mutation, render, native GUI, Owner media, and external Export dispatch: not performed.

## Independent final review

- Tester: PASS.
- Critic: TECHNICAL GO.
- Judge: TECHNICAL GO.
- Severity: Critical 0 / High 0 / Medium 0 / Low 0.
- Unresolved findings: none.

## Remaining integration gates

Technical implementation is complete. The remaining work is the normal integration transaction:

1. push the dedicated branch and create the Japanese Draft PR;
2. obtain Hosted OS matrix and repository checks;
3. follow the exact shared CHANGELOG lock sequence without modifying another lane's reservation;
4. merge only after the normal review and authority gates;
5. close/release the CHANGELOG lock and perform fresh-main read-back.

Hosted OS matrix, real WebView, real machine, Provider, Resolve, and native execution remain `NOT_CONFIRMED`; they are not claimed as completion evidence for this no-native Atomic Unit.

## Resume boundary

Resume from this file and the exact branch/HEAD above. Do not reopen the historical 2026-08-24 NO-GO checkpoint as current state. Do not touch user-owned `tmp/`, BAI Development OS, Provider/model configuration, Audio authority, Resolve apply/render, or shared CHANGELOG/Registry paths outside a separately authorized exact integration lock.
