# TASK-098 A2-R2b1 Durable Coordinator Pre-mutation Review

## 1. Identity, authority and decision requested

- Active Project / Task: `BAI VIDEO PRODUCTION / TASK-098`.
- Candidate Atomic Unit: `A2-R2b1 — durable control coordinator`.
- Current HEAD: `513d2e0a7e61ca354406ddeb0feebdfd23a6f8ff`.
- Base / current local main: `28ba61e5f01047a716c681a3584be22500fe53fc`.
- Branch: `codex/task-098-universal-wav-review-integration`.
- Governance: `DEV-3 HIGH ASSURANCE`.
- Owner authority: autonomous staged UWR integration, subject to all existing
  Human, native, private-media, Provider/model, Release and Production gates.

This review requests allocation for one narrow R2b responsibility: build and
fake-test the durable coordinator that owns control-row CAS ordering and
hash-addressed immutable control Evidence. It does not connect the coordinator
to the Provider, TASK-036 execution engine, Shell or Human confirmation route.
No implementation authority exists until independent Critic, Tester and Judge
accept the exact allocation in section 9.

## 2. Current state and direct dependencies

- A2-R2a is complete at `513d2e0a`; its six immutable record types, concrete
  lease fact and pure fail-closed reducer are canonical for this Unit.
- The existing `operations` table is sufficient and no schema migration is
  required. The ordinary CAS lacks an atomic expected-attempt predicate, so
  R2b1 must add one optional, default-off `expected_attempt` predicate to
  `compare_and_set_operation_status`. Pre-read attempt checks alone permit an
  ABA rollback/re-admission with the same ref.
- TASK-036 already owns the main v2 operation, permanent source lease and fixed
  output slot. R2b1 does not create a competing queue or lifecycle.
- The current engine creates the per-operation publication directory before
  Provider entry. R2b2 must later replace that behavior with parent-only
  preflight so a pre-publication closure can prove exact generation absence.
  R2b1 does not change that engine behavior.
- FasterWhisper currently consumes the lazy segment iterable internally and has
  no cooperative checkpoint. That belongs to R2b2 and is not changed here.

## 3. Why R2b is split

The accepted A2-R2 design combines three different failure domains:

1. durable record and CAS truth;
2. lazy Provider iteration and cooperative stop;
3. Product/Shell/Human application.

R2b1 closes only the first. R2b2 may later integrate a reviewed coordinator
with a fake-only Provider checkpoint path. R2c may later expose trusted
presentation and the single-use Human decision route. No later Unit may weaken
or bypass the R2a records or R2b1 CAS ordering.

## 4. Canonical state and immutable Evidence boundary

The existing SQLite operation rows remain the only state authority.

R2b1 defines one canonical pure `derive_runtime_operation_key_v2` helper from
the exact existing R1b inputs: project ID, source Asset ID/SHA, Provider ID,
model ID, execution-config SHA and validated R1a runtime-request record. The
existing TASK-036 v2 binding is mechanically changed to call this helper, with
golden before/after identity tests. The coordinator therefore derives the
expected main idempotency key independently from provenance-bound inputs; it
never treats the row's own key or a caller-provided expected key as proof.

R2b1 reserves one deterministic control operation:

- command type: `task098.runtime_transcription.control.v1`;
- idempotency key: `task098-runtime-control-<sha256>` derived with a dedicated
  domain from production Job, project, source Asset identity, source SHA and
  main v2 operation ID;
- initial state: `PENDING / null / attempt 0`.

The control row alone decides the current transition. Immutable JSON record
files are Evidence for the exact hash referenced by the row or its predecessor;
they are not a second state store:

- injected trusted root: the canonical resolved TASK-036 output directory,
  passed directly to an internal Evidence-store object and never accepted from
  Shell/JavaScript;
- root: `<trusted-output-root>/.task036-runtime-control/<main-operation-id>/`;
- ordinary file name: `<record-kind>-<64-lower-hex>.json`;
- crash-resume anchor: `generation-absence.json` and `terminal-commit.json` are
  fixed-role, create-only files inside that one operation directory. Their
  contents still carry and validate their exact record digest, barrier and
  predecessor refs. They are never overwritten or selected by enumeration;
- bytes: canonical JSON of exactly one validated R2a record;
- write: create-only or exact-byte idempotent read-back through pinned,
  non-reparse directories;
- read: only by an exact digest already named by the authoritative control row
  or a validated predecessor. Directory enumeration, newest-file selection and
  filename-only trust are prohibited.

An unreferenced candidate file has zero authority and may remain after a losing
CAS. The deterministic fixed-role path is the exact Evidence locator derived
from the authoritative main operation ID and winning control barrier; it is not
a scan or competing state value. The anchors are usable only when their
validated barrier/closure chain equals the authoritative control/main rows.
They let a process resume after observation or main CAS without forbidden
directory enumeration. R2b1 never deletes, overwrites, repairs or promotes
Evidence. The coordinator does not store transcript/source bodies, paths,
model identity or secrets in a control record.

The Evidence-store dependency is exact: it owns the injected resolved output
root, reuses `_PinnedDirectory` for parent/child identity and create-only stable
read/write, and exposes fault hooks only at named test boundaries. Reparse,
symlink, non-directory, unreadable, oversized, changed-identity and residual
temporary conflicts fail closed. It does not import the TASK-036 engine or any
Provider. R2b1 also owns one cross-process generation-exclusion lock beneath
the control root; R2b2's future first-generation writer must use that exact
lock before competing for the publication barrier and hold it through its first
immutable write.

## 5. Exact coordinator inputs and revalidation

Every mutating entry receives a frozen coordinate object containing only:

- production Job ID, project ID, source Asset ID and SHA-256;
- main v2 operation ID and expected attempt;
- validated R1a runtime request and decision plus Provider ID, model ID and
  execution-config SHA used to independently derive the main operation key and
  exact admission ref;
- fixed output-slot operation ID;
- R1b recovery classification as an advisory input. Human closure additionally
  requires literal `ADJUDICATION_REQUIRED_NO_PUBLICATION`, but the coordinator
  recomputes every concrete condition and never trusts that string alone.

Before each CAS, the coordinator reads and validates concrete Product rows.
Every main-operation CAS additionally supplies the same exact
`expected_attempt` to the SQL predicate:

- permanent v2 lease command/key/status/attempt/owner ref;
- main operation job/command/key/status/attempt/result ref;
- output slot job/command/key/status/result ref;
- control row command/key/status/attempt/result ref;
- source-bound admission ref and every supplied immutable record/predecessor.

No `lease_valid`, `slot_owned`, `generation_absent`, `provider_stopped` or
similar proof boolean is accepted. Caller-supplied records are reconstructed
through their exact R2a `from_dict` validator before use.

Revalidation is stage-specific. Before a barrier/main closure, the main row must
retain its exact admission/attempt. After a successful main CAS it must be
`FAILED / exact closure-ref / same attempt`; after control commit the control
row must be `COMPLETED / exact terminal-commit-ref`; after slot release the slot
may be `PENDING / same main-operation-id`. A resumed later stage never requires
or fabricates a former pre-commit state.

## 6. Closed transitions and ordering

### 6.1 Cancel request

`request_cancel` first validates main `IN_PROGRESS / exact admission`, permanent
lease and exact slot ownership. It derives a stable request from the control
operation ID and creation timestamp, writes/read-backs its immutable Evidence,
then CASes only:

`control PENDING / null -> IN_PROGRESS / exact cancel-request-ref`.

Duplicate requests return the exact existing request. A publication/terminal
barrier winner, foreign ref or changed coordinate returns a no-effect conflict.

The request derivation is exact: `cancel_request_id` is the deterministic
control row's `operation_id`; `requested_at` parses its canonical millisecond
`created_at`, converts to UTC, drops fractional seconds and emits
`YYYY-MM-DDTHH:MM:SSZ`; all remaining fields come from validated coordinates
and R1a records. The existing R2a cancel-request domain computes the record
digest. The same control row therefore reproduces byte-identical JSON and
digest after restart; malformed/non-UTC creation time fails closed.

### 6.2 Publication barrier

`acquire_publication_barrier` revalidates the same facts, writes/read-backs the
candidate barrier, then CASes only:

`control PENDING / null -> IN_PROGRESS / exact publication-barrier-ref`.

No immutable generation writer may be called before this method returns the
winning barrier. A cancel request that wins first therefore prevents every
later publication write. A publication winner makes cancel and Human closure
unavailable.

### 6.3 Cancel outcome and terminal barrier

Only a validated R2a cancel outcome whose request digest is the authoritative
request may CAS:

`control IN_PROGRESS / exact request-ref -> IN_PROGRESS / exact outcome-ref`.

`STOP_NOT_CONFIRMED` ends here and grants no barrier, main-operation CAS or slot
release. A confirmed cancel outcome may write/read-back a terminal barrier and
CAS only:

`control IN_PROGRESS / exact request-or-outcome-ref -> PARTIAL / exact barrier-ref`.

### 6.4 Human terminal barrier

R2b1 may accept a validated R2a Human decision only as an internal, unexposed
method for later R2c composition. It requires main `PARTIAL / exact admission`,
R1b classification `ADJUDICATION_REQUIRED_NO_PUBLICATION`, exact lease/slot and
control `PENDING / null`, then CASes only:

`control PENDING / null -> PARTIAL / exact Human terminal-barrier-ref`.

R2b1 creates no confirmation token, UI action or JavaScript surface.

Publication-versus-Human closure uses the same `PENDING / null` control-row CAS
and the same generation-exclusion lock. Cancel-versus-Human is not a valid
simultaneous state because their exact main statuses differ, but stale snapshots
must still be raced and prove that at most one path changes the control row.

### 6.5 Generation observation, main closure, commit and slot release

The publication contender and terminal contender serialize on the coordinator's
cross-process generation-exclusion lock. The publication path must acquire the
lock before its barrier CAS and hold it through the first immutable-generation
write. The terminal path holds the same lock across terminal-barrier CAS,
generation observation and main terminal CAS. Therefore an accepted absence
cannot race a cooperating writer between observation and main CAS; after a
terminal-barrier winner, every later writer loses before writing. R2b1 tests
this contract with an injected fake writer; R2b2 must prove the real writer uses
it before activation.

While holding the lock after a terminal barrier wins, a pinned reader checks the
exact `.task036-publications/<main-operation-id>` child. Complete nonexistence
(including absence of the publications parent) is `EXACT_GENERATION_ABSENT`.
Any file, directory, symlink/reparse point, partial set, unreadable state or
observation error is `PRESENT_PARTIAL_OR_UNKNOWN`. It performs no deletion or
repair. A test-only fault that creates/replaces the generation after the first
check must be caught by an immediate locked re-observation before the main CAS;
any difference blocks closure.

Only `EXACT_GENERATION_ABSENT` permits this ordered sequence:

1. write/read-back the exact observation;
2. CAS main operation from its exact pre-terminal state/ref to
   `FAILED / exact no-replay closure-ref`;
3. construct and write/read-back the terminal commit proving that CAS;
4. CAS control `PARTIAL / exact barrier-ref -> COMPLETED / exact terminal-commit-ref`;
5. revalidate lease, main closure, completed control commit and exact slot
   owner, then CAS slot `IN_PROGRESS / main-operation-id -> PENDING / same
   main-operation-id`.

No rollback occurs after terminal-barrier acquisition. Any failure before step
2 leaves the main operation unchanged and the barrier durable. Failure after
step 2 leaves the main operation terminal failed and the slot retained until
the exact remaining commit/release steps are resumed. Slot release is never a
compensation for a failed earlier step.

The main closure matrix is closed. Confirmed cancel accepts only main
`IN_PROGRESS / exact source-bound admission / exact attempt`; either confirmed
cancel outcome closes it to `FAILED / task098-runtime-cancelled:v1:<exact
outcome-digest>`. Human closure accepts only main `PARTIAL / exact source-bound
admission / exact attempt`, advisory recovery state
`ADJUDICATION_REQUIRED_NO_PUBLICATION`, and a validated Human decision; it
closes to `FAILED / task098-runtime-adjudicated-failed:v1:<exact
decision-digest>`. Every other main status/ref/attempt/closure-kind combination
has zero main, control and slot effect.

If a process dies after writing `generation-absence.json`, resume reads that
fixed anchor, validates its exact winning barrier, re-observes absence under the
same lock and then attempts the main CAS with atomic expected-attempt. If it dies
after main CAS or after writing `terminal-commit.json`, resume reads the fixed
anchors, validates the exact main closure and predecessor chain, completes only
the missing control CAS, and finally performs only the exact slot-release CAS.

## 7. Crash and concurrency matrix

Tests must inject a crash or CAS loss at each boundary:

| Boundary | Required durable result | Replay/release |
|---|---|---|
| candidate record written, CAS not won | authoritative row unchanged; candidate inert | none |
| cancel request wins before publication | publication barrier loses | none until confirmed closure |
| publication barrier wins before cancel | cancel request loses | publication path only |
| outcome ref bound, no terminal barrier | request/outcome remains resumable | none |
| terminal barrier bound, generation unknown/present | main unchanged, slot retained | none |
| exact absence written, main CAS not won | barrier retained | none |
| main failed closure committed, control commit missing | main failed, slot retained | no Provider replay |
| control terminal commit bound, slot release CAS lost | main/control terminal, slot retained | exact release resume only |
| exact slot release completed | terminal rows unchanged, slot reusable | no replay |

Thread and process races must prove exactly one winner in both invocation orders
for publication barrier versus cancel request, publication barrier versus Human
terminal barrier, stale cancel versus Human closure, and duplicate terminal
closure attempts. Lock-aware fake-writer tests must include generation creation
after the first observation and prove it blocks the main CAS. Tests may use only
fake/synthetic bytes beneath pytest `tmp_path` or a unique system-temp root.

## 8. Public/API and side-effect boundary

- R2b1 is internal Python only. It has no Shell, CLI, JavaScript, network,
  Provider, model or native entrypoint.
- It never calls FasterWhisper, constructs a model, reads private media or
  publishes Transcript/SRT.
- It may mutate only fake-test SQLite rows and hash-addressed control Evidence
  beneath the test-owned output root.
- It does not modify existing launch-config serialization or v1 behavior.
- TASK-097/TASK-046 Voice Dataset, second learning run, final model selection
  and voice optimization remain outside TASK-098.

## 9. Proposed exact R2b1 allocation

Implementation may modify only after Judge acceptance:

1. `src/ai_video_production/task098_runtime_transcription_coordination.py`
   (new internal coordinator);
2. `src/ai_video_production/store.py` (only an optional, default-off atomic
   `expected_attempt` predicate on ordinary operation CAS);
3. `src/ai_video_production/task036_product_ports.py` (only replace the existing
   v2 operation-key calculation with the new canonical pure helper; no control,
   Provider or lifecycle integration);
4. `tests/test_task098_runtime_transcription_coordination.py`
   (new fake/store/filesystem/concurrency/crash tests);
5. `tests/test_idempotency.py` (generic expected-attempt/ABA regression only);
6. `tests/test_task098_task036_runtime_managed_transcription.py` (operation-key
   golden parity/regression only);
7. bounded `docs/ai-team/current-state.md`, `docs/ai-team/task-index.md` and
   `docs/ai-team/tasks/TASK-098/**` status/Evidence.

Explicitly not allocated: `faster_whisper_asr.py`, TASK-036 Shell/launcher/CLI,
schemas, packaging,
dependencies, native adapters or any TASK-097/046 file.

## 10. Acceptance

1. No database migration and no second state authority exists.
2. Every record is exact R2a canonical JSON, digest-addressed, create-only or
   exact-byte idempotent and loaded only from an authoritative digest chain.
3. Missing, oversized, malformed, tampered, foreign, symlink/reparse or changed
   record Evidence fails closed with no CAS/release.
4. Concrete lease/main/slot/control rows are revalidated before every mutation.
5. Canonical v2 operation-key golden tests prove the coordinator and existing
   R1b binding use one provenance-derived identity with no row-self-validation.
6. Main CAS predicates atomically include exact attempt and ABA tests prove a
   re-admitted attempt cannot be closed by a stale coordinator.
7. The closed transition list is exhaustive; every other status/ref pair has
   zero effect.
8. Publication/cancel/Human races in both orders produce exactly one control-row
   winner; stale cancel/Human snapshots have no second effect.
9. `STOP_NOT_CONFIRMED` never reaches terminal barrier/main CAS/release.
10. Exact generation absence is observed only after a terminal barrier while the
   shared writer lock is held; late generation injection or any
   presence/uncertainty retains the slot.
11. Main terminal CAS uses the exact closure-kind matrix, precedes terminal
   commit, and terminal commit precedes exact
   slot release.
12. Fixed observation/commit anchors permit enumeration-free resume after every
    crash point and reject a foreign barrier/closure/attempt.
13. Stable cancel-request derivation reproduces byte-identical Evidence from the
    same control row across process restart.
14. Crash/resume tests cover every row in section 7 without Provider replay.
15. Human decision support remains internal and requires the exact typed R1b
    adjudication state; no UI/confirmation token is introduced.
16. R2a focused and R1b operation/store regressions remain green.
17. Independent Critic, Tester and Judge have zero unresolved Critical/High.
18. External Evidence is persisted and read back before commit.

## 11. Review request and next boundary

Independent Critic must review state authority, Evidence-vs-state separation,
CAS ordering, crash recovery, generation observation and slot release. Tester
must verify that the six-file ceiling can cover the matrix without production
effects. Judge may accept, reject or narrow only R2b1.

Even if accepted and completed, R2b1 does not make R2b complete. R2b2 Provider/
engine integration and R2c Shell/Human application each require a later fresh
pre-mutation review and exact file allocation.

## 12. Review outcome

- Independent Critic: initial `REJECT / 0 Critical / 3 High / 2 Medium / 0 Low`;
  final `ACCEPT / 0/0/0/0` after the attempt-CAS, identity, anchor, lock, request
  derivation and closure-matrix corrections.
- Independent Tester: initial `FAIL / 0/2/1/0`; final `PASS / 0/0/0/0` after
  Human/publication races, late-generation exclusion and pinned-I/O fault
  contracts were added.
- Independent Judge: `ACCEPT / R2b1 LIMITED IMPLEMENTATION ALLOCATED / 0/0/0/0`.
- Allocation: only the six source/test files in section 9 plus bounded docs.
- R2b2/R2c, Provider execution, engine lifecycle connection, Shell, native and
  private/external effects remain unallocated.
