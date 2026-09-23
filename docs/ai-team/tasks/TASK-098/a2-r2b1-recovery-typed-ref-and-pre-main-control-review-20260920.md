# TASK-098 A2-R2b1 Recovery — Typed Refs and Pre-main Control Revalidation

## 1. Recovery identity

- Active Project / Task / Unit: `BAI VIDEO PRODUCTION / TASK-098 / A2-R2b1 Recovery`.
- Worktree / branch: `C:\home\baisound\projects\bai-video-production\.worktrees\task-098-universal-wav-review-integration` / `codex/task-098-universal-wav-review-integration`.
- HEAD: `4c1fedb039218078a1479006c71d41c433f53ba0`.
- Governance: `DEV-3 HIGH ASSURANCE`.
- Preserved implementation checkpoint: `C:\home\baisound\evidence\bai-video-production\TASK-098\a2-r2b1-durable-coordinator\20260920T160000+0900\checkpoint.md`, SHA-256 `355f1a998b6abf23d5fa4f3ef6d5fba394bffe3d7515204348dc91a922b42b8b`, full read-back `PASS`.

Final Judge rejected the otherwise bounded R2b1 diff with two High findings.
This Recovery does not claim commit readiness and does not allocate R2b2,
Provider, engine lifecycle, Shell, native, private media, model or training work.

## 2. Canonical contradiction resolution

There is no Owner or design authorization to replace typed durable refs with
bare record digests. The canonical A2-R2 design section `Typed durable refs are
exactly` remains authoritative:

- cancel request: `task098-runtime-cancel-request:v1:<64 lower hex>`;
- cancel outcome: `task098-runtime-cancel-outcome:v1:<64 lower hex>`;
- publication/terminal barrier: `task098-runtime-commit-barrier:v1:<64 lower hex>`;
- terminal commit: `task098-runtime-terminal-commit:v1:<64 lower hex>`.

The record fields and immutable Evidence filenames continue to use canonical
`sha256:<64 lower hex>` record digests. Only SQLite control-row `result_ref`
uses the typed durable reference. Parsing must full-match the exact prefix and
lower-case digest, recover the canonical `sha256:` digest, and reject bare
digests, unknown kinds/versions, upper-case hex, suffixes and cross-kind refs.
Main-operation no-replay closure refs remain the already-canonical
`task098-runtime-cancelled:v1:` or
`task098-runtime-adjudicated-failed:v1:` values.

## 3. Exact correction allocation

Only two already-allocated R2b1 files may change for this Recovery:

1. `src/ai_video_production/task098_runtime_transcription_coordination.py`
   - add one closed typed-ref formatter/parser;
   - store and CAS only typed request/outcome/barrier/commit refs on the control row;
   - convert a validated typed ref back to its canonical digest only for exact
     immutable Evidence loading;
   - before the main terminal CAS, revalidate control as exact
     `PARTIAL / typed barrier ref / attempt 0` in addition to lease, main and
     slot; retain existing post-main/pre-control and pre-slot validations.
2. `tests/test_task098_runtime_transcription_coordination.py`
   - assert exact typed refs at every control stage and terminal resume;
   - reject bare digest, wrong-kind/version/case/suffix refs with zero main/slot effect;
   - mutate control at the `after_generation_observation` boundary and prove
     main remains at its pre-terminal state, control is not promoted and slot is retained;
   - keep all existing crash/race/tamper tests green.

No store, TASK-036 port, other test or schema change is needed. The existing
optional `expected_attempt` store predicate and canonical operation-key helper
remain unchanged.

## 4. Acceptance

1. Every control-row non-null ref is one of the four exact typed durable refs.
2. Bare digests and cross-kind or noncanonical refs never authorize Evidence
   loading, CAS, main closure, control commit or slot release.
3. Evidence remains digest-addressed canonical JSON and is not renamed or made
   authoritative independently of SQLite.
4. Immediately before main `FAILED` CAS, lease, exact pre-terminal main,
   slot `IN_PROGRESS` ownership and control `PARTIAL / typed barrier / attempt
   0` are all re-read and validated.
5. Existing pre-control-CAS and pre-slot-release revalidation remains intact.
6. Focused tests and the TASK-006/023/036/098 direct regression pass.
7. Independent Critic and Judge report zero unresolved Critical/High; final
   commit readiness still requires a fresh external checkpoint reflecting the
   corrected hashes and tests.

## 5. Requested decision

Critic/Judge may accept or reject only this two-file corrective allocation.
Acceptance authorizes one bounded Recovery correction and retest; it does not
authorize additional review/fix cycles or any R2b2/R2c effect.

## 6. Recovery outcome

- Implementation remained inside the exact two-file Recovery allocation.
- Exact malformed control-ref cases (bare digest, wrong kind, wrong version,
  upper-case digest and suffix) fail closed without main/slot effects.
- The pre-main fault test keeps `PARTIAL / attempt 0` but replaces the winning
  barrier ref with a different valid typed barrier ref; main remains
  `IN_PROGRESS`, the control row is not promoted, terminal commit is absent and
  the output slot remains owned.
- Focused verification: `42 PASS`.
- Direct TASK-006/023/036/098 regression: `354 PASS`.
- Final Critic: `ACCEPT / 0/0/0/0`.
- Final Tester: `PASS / 0/0/0/0`.
- External checkpoint read-back: `PASS`, SHA-256
  `82484a0f1a9cb71ee5065ec9072f342f0a5d1063079f1a70a17e26c72365c2df`.
- Final Judge: `ACCEPT / COMMIT_READY / 0/0/0/0`.
