# TASK-058 Windows concurrency corrective authorization

Unit identity: `TASK058-WINDOWS-CONCURRENCY-CORRECTIVE-V1`

Status: `AUTHORIZED_IMPLEMENTATION / DEV-4 / JUDGE_PASS / COMMIT_READY`

## 1. Authority and historical boundary

The Owner assigned this bounded corrective after TASK-069 reached a frozen design-review checkpoint. It is a continuation of TASK-058's canonical admission transaction responsibility and does not reopen, negate, or relabel the released TASK-058 history.

The exact defect is the hosted Windows 3.11 failure of `test_multiprocess_generic_and_exact_project_writes_serialize[exact]`: an Exact writer and a Generic writer use different stable journal locks while touching the same Product Project and Generic journal namespace. A Windows namespace collision can therefore escape from the Generic worker as raw `PermissionError [WinError 5]` instead of a Product-domain failure.

The correction must establish one stable operation-lock domain for Exact and Generic effect-bearing operations, preserve the existing transaction semantics, and translate boundary OS/lock failures to a fixed body-free Product-domain error. Catching and hiding the error, weakening the assertion, accepting raw `OSError`, or declaring an expected failure is not completion.

## 2. Current bind

- Repository: `baisound/bai_video_production`
- Base and current HEAD: fresh `origin/main@70ba9e369887d3d7ded59e7197d20d133b2b4d38`
- Branch: `codex/task-058-windows-concurrency-corrective-v1`
- Worktree: `C:/Users/user/.codex/visualizations/2026/08/29/01a04d4b-8e43-7b23-9feb-c32019b11d43/task-058-windows-concurrency-corrective-v1`
- Initial dirty state: clean
- Open-PR overlap for all three Allowed Files: zero
- Existing TASK-058 A2 lock affecting the two source/test paths: `HOSTED_CLOSED_RELEASED`; no live lock or sole-writer collision was found
- Sole writer for this Unit: `/root`

Any HEAD/base drift, new target-path PR overlap, unknown dirty path, or live work-lock reclaims mutation as STOP pending a fresh bind.

The worktree was initially bound at `c27c24d6cb5f936e0549b743084bb9a9eaceb545`.
When `origin/main` advanced, the two upstream commits were inspected before any
further mutation.  Their only changed Product path was the unrelated new
`docs/ai-team/tasks/TASK-063/complete-design-packet.md`; Allowed File overlap was
zero.  The worktree then fast-forwarded to `70ba9e369887d3d7ded59e7197d20d133b2b4d38`
with all owned dirty-file SHA-256 values preserved exactly.

## 3. Allowed and prohibited files

Allowed Files are exactly:

1. `src/ai_video_production/montage_learning_canonical_admission_transaction.py`
2. `tests/test_task058_montage_learning_canonical_admission_transaction.py`
3. `docs/ai-team/tasks/TASK-058/task058-windows-concurrency-corrective-authorization.md`

Must not modify: `atomic.py`, `secure_authority_io.py`, TASK-067/TASK-069/TASK-072 files, schemas, package/shared current-state/task-index/roadmap/CHANGELOG, workflows, Release/install/Deploy/Production state, or any external/native data.

## 4. Owned symbols and intended change

Source ownership is bounded to:

- a private shared-operation lock wrapper in `montage_learning_canonical_admission_transaction.py`;
- `MontageLearningCanonicalAdmissionTransactionStore.admit_exact`;
- `MontageLearningCanonicalAdmissionTransactionStore.admit_generic_observation`;
- `MontageLearningCanonicalAdmissionTransactionStore.recover_generic_observation`;
- only the minimum fixed error translation required at those public operation boundaries.

The shared operation coordinate is the already-stable Exact transaction lock domain selected by `exclusive_file_update_lock(self.journal_path)`. Generic admission/recovery enters that same domain before its existing Generic journal lock. The Exact path retains the same shared domain it already uses. No new canonical file, store, receipt, revision, or public API is introduced.

Test ownership is bounded to the existing multiprocessing helpers and tests in the one Allowed test file, plus new focused fault/lock-order cases in that file.

## 5. Lock order and invariants

The only permitted nested order is:

1. shared canonical-admission operation lock: the stable sibling lock of `self.journal_path`;
2. Generic journal lock, Generic operations only: the stable sibling lock of `self.generic_journal_path`;
3. Product Project lock;
4. external anchor lock, Exact operations only.

No code may acquire the shared operation lock while holding the Generic, Product, or anchor lock. No reentrant acquisition of the shared lock is permitted. The shared lock remains held from pre-journal classification through Project save/recovery, terminal readback, and journal cleanup. Existing read-only lookup lock order remains unchanged and may not create or promote authority.

Every success, typed rejection, exception, and recovery path releases each acquired lock exactly once. An acquisition or release `OSError`/unsafe-lock failure is exposed only as `MontageLearningCanonicalAdmissionError` with fixed text `RECOVERY_REQUIRED: canonical admission operation unavailable`, using no exception chaining, raw path, OS error, errno, or Win32 detail. A failure after an ambiguous effect preserves journals/artifacts and does not retry, overwrite, unlink, or claim success.

## 6. Focused fault and negative matrix

| ID | Fixture or seam | Required result | Filesystem/result oracle |
|---|---|---|---|
| WC-01 | Exact and Generic spawned together; `delayed_worker=exact` and `generic`, repeated | shared operation lock serializes the complete writers; each worker returns only Product-domain result/error | no raw `PermissionError`/`OSError`/`WinError`; journals converge absent; both canonical results verify |
| WC-02 | Generic journal creation/replace seam while Exact is ready to inspect Generic state | Exact cannot enter the shared critical section until Generic reaches terminal/recovery boundary | foreign/unrelated bytes unchanged; no concurrent journal read/replace |
| WC-03 | shared-lock enter raises `OSError` or unsafe-lock `ValueError` | fixed `MontageLearningCanonicalAdmissionError`; operation body call count zero | Project/anchor/journal/ledger/receipt delta zero; public text body-free |
| WC-04 | shared-lock exit raises after body failure or terminal | fixed Product-domain error; original effect classification remains recoverable from durable state | no retry/cleanup/overwrite; no raw exception/path detail |
| WC-05 | Generic and Generic same-CAS writers under the shared domain | exactly one `ACCEPTED`; loser is typed or exact duplicate/stale per existing contract | no split journal, manifest, ledger, object, marker, or receipt generation |
| WC-06 | lock-order instrumentation for Exact, Generic admit, and Generic recovery | observed order is an exact prefix of shared -> Generic if applicable -> Product -> anchor if applicable | nested/reentrant shared acquisition zero; deadlock/timeout zero |
| WC-07 | one worker fails after Generic journal write while the other waits | waiting worker starts only after first lock release, then follows existing bounded recovery | preserved journal is recovered once; raw exception/path leak zero; unrelated delta zero |

## 7. Verification and DEV-4 gate

Required order:

1. compile/static and diff-scope checks;
2. focused lock/error negatives `WC-01..WC-07`;
3. existing TASK-058 canonical admission transaction test file;
4. directly impacted TASK-058 bridge/adapter regression where required by changed behavior;
5. Windows spawn repetitions for both delayed-worker variants;
6. independent DEV-4 Tester and Critic;
7. bounded fixes and retest, at most two review/fix cycles;
8. independent Judge with Critical/High `0/0` before commit.

Commit, push, and Draft PR remain stopped until the exact source/test/doc diff is in scope, all required executed tests pass, and independent DEV-4 Critical/High are `0/0` with Judge PASS. Release, install, Deploy, Production Activation, shared-document mutation, force push, and destructive cleanup remain unauthorized.

## 8. Review fix cycle 1 checkpoint

The first frozen implementation review found no Critical issue.  The independent
Tester returned `PASS / C0 H0 M1`; the independent Critic returned
`FAIL / C0 H2 M4`.  The accepted findings and bounded corrections are:

- sanitize the fixed operation-lock error outside the caught exception so its
  public `__cause__` and `__context__` are both `None`;
- translate raw `OSError` and unsafe plain `ValueError` escaping any lower
  Generic, Product, or anchor lock while preserving existing
  `MontageLearningCanonicalAdmissionError` and `ProductError` results;
- observe the competing thread at the exact shared-lock acquisition seam before
  asserting it is blocked;
- inject exit failure before the underlying unlock, preserve the ambiguous
  terminal/pending state, and release the retained test guard only as fixture
  cleanup before bounded recovery;
- close Generic same-CAS object/marker/manifest/ledger cardinality and unrelated
  byte preservation;
- trace all Generic finish/recovery Product acquisitions, not only the first
  Product save call;
- refresh the base/HEAD bind from the initial commit to current
  `origin/main@70ba9e369887d3d7ded59e7197d20d133b2b4d38` after proving Allowed File
  overlap zero.

Executed verification after those corrections:

- bundled Windows Python `py_compile`: `PASS`;
- WSL focused WC lock/error/recovery selection: `32 passed`;
- WSL canonical admission plus directly impacted bridge/contracts/adapter:
  `228 passed, 6 skipped`; the five platform skips are Windows-only handle or
  junction fixtures and the sixth is the unavailable installed-SKILL fixture;
- native Windows standard-library actual-source subprocess smoke, Exact-delayed
  and Generic-delayed, three repetitions each: `6 / 6 PASS`;
- native Windows shared-lock enter/exit fault smoke across Exact/Generic and
  terminal/pending states, including `__context__ is None`: `8 / 8 PASS`;
- Ruff was not installed in the existing WSL runtime and was recorded
  `NOT_CONFIRMED`; no install or dependency mutation was attempted;
- `git diff --check`: `PASS`.

This checkpoint is not the final Judge receipt.  Independent Tester/Critic
recheck and Judge `C/H=0` remain required before COMMIT STOP can be lifted.

## 9. Review fix cycle 2 checkpoint

The first independent recheck agreed on one remaining High issue.  The public
operation wrapper translated every plain or typed `ValueError`, so an existing
bridge-contract rejection, durable-staging rejection, or caller callback could
be mislabeled as a lock outage.  The Tester returned `FAIL / C0 H1 M0`; the
Critic returned `FAIL / C0 H1 M1` where the Medium was the missing preservation
regression.

The bounded second-cycle correction:

- retains the public fallback only for otherwise-untranslated raw `OSError`;
- introduces a private lock-boundary adapter whose conversion scope is exactly
  guard factory, `__enter__`, and `__exit__`;
- applies that adapter to the shared, Generic, local Product, and anchor lock
  guards used by effect-bearing Exact/Generic operations;
- preserves body exceptions because the adapter does not catch exceptions
  propagated from the guarded operation body;
- adds explicit preservation negatives for
  `MontageLearningBridgeContractError`,
  `MontageLearningDurableStagingReadbackError`, and a caller callback's exact
  plain `ValueError`;
- keeps the internal Product-save lock's real raw `OSError` boundary covered
  while preserving its existing typed `ProductError` contract.

Executed verification after this correction:

- bundled Windows Python `py_compile`: `PASS`;
- focused lock and error-preservation selection: `32 passed` after correcting
  the test oracle to include the deliberately persistent stable lock files;
- TASK-058 canonical admission transaction file: `115 passed, 5 skipped`;
- canonical admission plus directly impacted bridge/contracts/adapter:
  `231 passed, 6 skipped`; the five platform skips are Windows-only handle or
  junction fixtures and the sixth is the unavailable installed-SKILL fixture;
- native Windows actual-source domain/boundary smoke covering Generic contract,
  Exact durable-staging, callback `ValueError`, and lower Generic lock failure:
  `4 / 4 PASS`;
- native Windows actual-source spawned Exact/Generic serialization, both
  delayed-worker orders and three repetitions each: `6 / 6 PASS`;
- `git diff --check`: `PASS`.

Independent final recheck of the frozen source/test/document candidate returned:

- Tester: `PASS / C0 H0 M0 L0`; independently executed focused `32 / 32`
  and the complete target test file `115 passed, 5 skipped`; Windows-native
  independent execution was `NOT_CONFIRMED` because the bundled runtime has no
  pytest, and was not conflated with the Builder's native evidence;
- Critic: `PASS / C0 H0 M0 L0`; actionable finding `0`, with the guard-only
  conversion scope, body-error preservation, lock order, ambiguous recovery,
  raw-leak boundary, Allowed Files, HEAD, and frozen hashes all verified.

The Judge gate remains pending.  COMMIT STOP is not lifted by Tester/Critic
PASS alone.

## 10. Completion receipt contract

The task-local completion receipt must bind exact source/test/document SHA-256 values, the shared stable operation-lock coordinate and lock order, the typed fixed error contract, executed focused/Windows/impacted regression results, raw OS/path/body leakage zero, independent Critic/Tester/Judge verdicts, and exact Git commit/branch/base. It is Evidence only and creates no runtime, Release, Deploy, or Production authority.

## 11. DEV-4 Judge receipt

The independent Judge reviewed source
`b2dccb9d0bf88a0082ef754486cad1b17f27afb6ee928f1bd0f961e7fe719dbb`,
test `c7505721490afd5ea5a927372390bb3d1d711c81bad841c4e60175fff21ac675`,
and the pre-receipt authority document
`2e614519147f02e5beffea02f21ca6e73cca8ffb613fc2bbc081753594f7b910`.
The verdict was `PASS / C0 H0 / actionable 0`, and COMMIT STOP was lifted for
those three Allowed Files only.

The Judge confirmed:

- Exact and Generic share the stable `journal_path` operation-lock coordinate;
- observed order is shared -> Generic if applicable -> Product -> anchor if
  applicable, with no reverse order or shared re-entry;
- fixed body-free conversion is limited to lock guard seams plus otherwise raw
  public-boundary `OSError`, while existing `ProductError`, domain error, and
  body `ValueError` semantics remain intact;
- raw OS/path/WinError text is absent from the public result;
- ambiguous unlock failures preserve durable state and require bounded recovery;
- spawned ordering, same-CAS, lock seam, error-preservation, and recovery
  negatives are sufficient;
- the dirty scope contains exactly the three Allowed Files.

Because embedding a document's own final SHA-256 is self-referential, the final
post-receipt document SHA-256 is bound by the staged diff, commit, Draft PR, and
an independent final-document rebind.  This receipt authorizes no Release,
Deploy, Production Activation, shared-document mutation, or native external
effect.
