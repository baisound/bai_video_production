# TASK-102 — Secure Project Manifest Transaction Broker

- Status: `PMST_D0_D1_I1_ACCEPTED / PMST_N1_COMPLETE / PMST_I2_AUTHORIZED / PMST_I2A_COMMITTED / PMST_I2B_BUILDER_COMPLETE`.
- Governance: `DEV-4 FOUNDATION CRITICAL`.
- Allocation authority: on 2026-09-27 the Owner answered `つぎへ` directly to the explicit JCV-N-D Human Gate asking whether to accept the service-SID broker architecture and allocate one new direct dependency Task. This records acceptance of allocation/design only.
- Responsibility predecessor: TASK-043 remains hosted-closed historical Project schema/store foundation and is not reopened.
- Direct consumer: TASK-099 JCV-N.
- Related dependency: TASK-068 immutable publication/readback remains independently owned and is not absorbed.
- First unused Task-ID audit: `TASK-102` is absent while TASK-100 and TASK-101 are already allocated in this worktree.
- Current implementation authority: PMST-N1 authority is consumed and complete. On 2026-09-29 the Owner explicitly authorized `PMST-I2`. This authorizes the bounded source/test writer-migration units recorded below. Product enrollment, service installation/update, ACL mutation, real Project writes, native QA, Release, Deploy and Production remain separate gates.

## Objective and responsibility boundary

Own one Product-wide secure transaction boundary for the existing canonical `.bai-project/project.json` manifest and the transaction-support objects that must remain writable inside its protected control directory. The broker must provide generic exact-predecessor compare-and-swap, durable same-operation outcome evidence, restart recovery and enrolled-root mutation exclusion for every canonical manifest writer. It must also mediate or reject every other existing `.bai-project` mutation/lock route before enrollment. It must preserve the current Project schema and must not create another Project store, selector, Timeline, Job, Asset, voice or currentness semantic owner.

TASK-102 owns the generic service/client/enrollment protocol, protected control-directory topology, non-selector transaction witnesses, manifest-writer migration, protected-object transport/lock replacement and compatibility/read-only rejection. Each caller continues to own its target-manifest, Job, history, backup, VoiceProfile, Timeline-recovery and other object semantics, Human authority and side effects. TASK-099 alone owns Project/Job currentness V2 semantics. TASK-068 alone owns immutable index publication/readback. TASK-043 history remains immutable.

The accepted prerequisite architecture is [TASK-099 JCV-N-D R1](../TASK-099/jcv-n-d-secure-native-backend-r0.md). This Task must not weaken its fail-closed gates or reinterpret design acceptance as native feasibility.

## Atomic Units

1. **PMST-D0 — allocation, source-derived writer/security inventory and feasibility contract.** Documentation only. Freeze every current manifest mutation/recovery route, protected namespace implications, threat model, native proof questions, migration order and exact later units. Independent Critic/Tester/Judge required.
2. **PMST-D1 — pure protocol/schema design.** Only after D0 acceptance. Define strict private IPC records, public-safe projections, enrollment and operation-witness schemas, transition invariants and fake-port failure matrix. No service/ACL/filesystem effect.
3. **PMST-I1 — pure service/client state machine and fake backend.** Exact files require a fresh allowed-files amendment after D1. No Windows service installation or real Project mutation.
4. **PMST-N1 — bounded Windows feasibility proof.** Requires an explicit native gate. Prove process identity, named-pipe admission, sharing barriers, ACL/owner behavior, concrete replacement/durability semantics and crash/restart witness recovery in an OS-unique contained root.
5. **PMST-I2 — Product writer migration.** Only after accepted N1 evidence. Route all current writers and recovery paths, block old/unmigrated writers, retain read-only compatibility and preserve caller semantics. No partial enrollment.
6. **PMST-C — canonical integration and enrollment UX.** Only after complete migration and native acceptance. Normal Product entrypoint integration, packaged verification and rollback/recovery UX remain separate exact gates.

## PMST-D0 exact scope

Allowed files:

1. `docs/ai-team/tasks/TASK-102/task.md`
2. `docs/ai-team/tasks/TASK-102/pmst-d-secure-project-manifest-transaction-broker-r0.md`
3. `docs/ai-team/tasks/TASK-099/task.md`
4. `docs/ai-team/tasks/TASK-099/jcv-n-d-secure-native-backend-r0.md`
5. `docs/ai-team/tasks/TASK-073/expression-master-wav-delivery-plan-r1.md`
6. `docs/ai-team/tasks/TASK-073/expression-master-wav-task-ledger-r1.json`
7. `docs/ai-team/task-index.md`
8. `docs/ai-team/current-state.md`
9. `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md`

Source, schema, test, installer, service, ACL, Product runtime, private media/model and external repository files are prohibited in D0. The canonical R0 delivery plan/ledger/review remain immutable; R1 records the newly discovered dependency and count change.

## PMST-D0 exit

- Owner allocation and the increase from 17 to 18 outstanding responsibility lanes are recorded without rewriting R0 history.
- Current manifest writer/recovery classes plus every non-manifest protected-directory writer and read-associated lock mutation are inventoried, and no partial-enrollment route is treated as safe.
- Concrete Windows feasibility questions and rejection criteria are explicit.
- Independent DEV-4 Critic/Tester/Judge accept the design with unresolved Critical/High findings zero.
- No native or Product effect occurs; required external Evidence is persisted and read back.

## PMST-D0 R1 independent decision

- Initial exact9 review: Critic/Judge `ACCEPT`, C/H/M/L `0/0/0/0`; Tester `REVISE`, C/H/M/L `0/1/0/0` because service-only `.bai-project` protection also blocks non-manifest writers and read-associated lock mutations.
- R1 correction: added jobs/history/autosave/backups/VoiceProfile/save-journal/Timeline-recovery and lock-only routes; required a complete physical mutation graph; limited broker operations to closed broker-derived targets and retained every semantic owner.
- R1 rereview: Critic/Judge `ACCEPT`, C/H/M/L `0/0/0/0`; Tester `PASS / ACCEPT`, C/H/M/L `0/0/0/0`.
- Accepted scope: responsibility allocation, inventory classes, security floor, design order and proof gates only. Full machine-checked inventory, protocol ABI, source implementation and Windows/native feasibility are not accepted by D0.
- Next unit: PMST-D1 pure protocol/journal/witness and complete migration-matrix design. No service/ACL/filesystem effect.

## PMST-D1 exact scope

Allowed files:

1. `docs/ai-team/tasks/TASK-102/task.md`
2. `docs/ai-team/tasks/TASK-102/pmst-d1-protocol-journal-migration-r0.md`
3. `docs/ai-team/tasks/TASK-102/pmst-d1-protected-control-mutation-matrix-r0.json`

D1 is documentation-only. It must choose one broker-owned journal model, freeze closed private protocol records and operation profiles, inventory every current `.bai-project` physical mutation/lock surface and bind each route to delegation, redesign or deterministic block. Source/schema/test/service/installer/ACL/native/Product mutations remain prohibited. Exit requires independent DEV-4 review with unresolved Critical/High findings zero and external Evidence readback.

## PMST-D1 Recovery R1 authority

On 2026-09-27 the Owner answered `つぎへtugih` directly to the explicit PMST-D1 Recovery R1 Human Gate. Recovery authority is limited to closing the two final-review High findings: exact participant phase/status/effect tuples and closed read/query evidence-unavailable result variants, followed by one fresh independent final review. It does not authorize source/schema/test/service/installer/ACL/native/Product, private media/model, Release, Deploy or Production effects.

## PMST-D1 Recovery R1 final decision

- Reviewed exact3 SHA256: `task.md` `3463db8dbf6b7034bfd478c98eb6392024de0756de0bf90989c29b144fe22313`; protocol design `a0e90cc03eb9078b616916af5d3771d3cdb06cd6c0f892d84ede18b705872447`; migration matrix `ad7f4a22a560b84c8e317b2e450c3097110877e04f25f0352cc62651439a8dd5`.
- Independent Critic/Judge: `ACCEPT`, C/H/M/L `0/0/0/0`.
- Independent Tester: `PASS / ACCEPT`, C/H/M/L `0/0/0/0`.
- Closed findings: participant phase/status/effect is an exact tuple union with monotonic known outcomes and UNKNOWN barrier closure; read/query evidence failures have distinct closed variants with exact witness/readback nullability and public-result mappings.
- Acceptance is documentation-contract acceptance only. Windows/native feasibility remains `NOT_CONFIRMED`, and implementation/native/Product effects remain unauthorized.
- The status and this decision block are the only post-review administrative changes to the reviewed exact3. PMST-I1 requires a fresh exact Allowed Files allocation before any implementation mutation.

## PMST-I1 authority and exact scope

On 2026-09-27 the Owner explicitly authorized TASK-102 PMST-I1 to design its exact Allowed Files and implement the pure state machine, fake backend, schema and unit tests through independent review. Windows service installation, ACL mutation, real Project writes, native QA, Release, Deploy and Production use were explicitly excluded.

Exact Allowed Files:

1. `docs/ai-team/current-state.md`
2. `docs/ai-team/tasks/TASK-102/task.md`
3. `docs/ai-team/tasks/TASK-102/pmst-d1-protocol-journal-migration-r0.md`
4. `src/ai_video_production/task102_project_manifest_transaction.py`
5. `schemas/task102-project-manifest-transaction.schema.json`
6. `src/ai_video_production/schema_resources/task102-project-manifest-transaction.schema.json`
7. `tests/test_task102_project_manifest_transaction.py`

PMST-I1 may implement only strict body-free protocol parsers, immutable operation profiles, a deterministic pure transition machine, an injected fake port, public-safe projections and focused schema/unit tests. It must not import filesystem, subprocess, socket, Windows/native, installer, ACL or existing Project writer/store modules; must not create a live backend; and must expose no path or arbitrary-byte operation. Exit requires exact7 scope verification, root/mirror schema identity, focused tests, targeted regression, independent DEV-4 Critic/Tester acceptance with unresolved Critical/High findings zero, commit-ready state and external Evidence readback.

## PMST-I1 Builder checkpoint

- Added strict parsers for intent, request, enrollment, participant plan/receipt, profile-validation receipt, phase result, journal, witness and public status records with domain-separated canonical digests, exact fields, byte/depth/time/ID bounds and duplicate-key rejection.
- Added immutable closed operation profiles, ACTIVE-enrollment/install/trusted-time binding, process/session/security-bound single-use nonce consumption, profile-specific journal routes, monotonic phase/effect/manifest observation checks, validated journal/witness/participant/readback evidence lookup, cross-record predecessor/successor/read/query/witness binding, admission-barrier rules and public-safe projection.
- Added only `ScriptedFakePmstPort`; `run_operation` rejects every non-fake port. The module imports no filesystem/process/socket/native/Project store implementation and performs no external write.
- Root/package schema bytes are identical and cover all external PMST-I1 records, participant tuples, phase/status/payload unions and public nullability/recovery mappings.
- Initial independent review returned Critic/Judge `REVISE` with C/H/M/L `0/5/2/0` and Tester `FAIL / REVISE` with C/H/M/L `0/1/0/0`. The bounded correction closes contradictory terminal/effect acceptance, unused evidence validators, missing admission/profile enforcement, known-outcome reconciliation projection, undeclared phase null acceptance and fake-port subclass acceptance.
- Focused WSL test after correction: `53 passed`.
- TASK-102 plus direct consumer TASK-099 regression after correction: `75 passed`.
- Runnable TASK-043 Project/Job/History regression: `66 passed`.
- `tests/test_task043_project_save_recovery.py`: `NOT_CONFIRMED`; collection stopped before code execution because the existing WSL environment lacks the already-declared `referencing` package. No dependency installation was attempted.
- Windows/native feasibility and real Project effects remain `NOT_CONFIRMED / UNAUTHORIZED`.
- Next gate: frozen corrected exact7 second and final independent DEV-4 Critic/Tester review. A remaining Critical/High finding stops this I1 cycle under the DEV-4 two-cycle budget.

## PMST-I1 final rereview and Recovery boundary

- Corrected exact7 independent rereview matched every frozen hash and the schema mirror. Critic/Judge returned `REVISE`, C/H/M/L `0/4/0/0`; Tester returned `FAIL / REVISE`, C/H/M/L `0/1/1/0`.
- Remaining High findings are: successor/committed-witness/readback/currentness content is not fully cross-bound; participant identity/sequence/observation is not fully bound to its plan and phase history; a committed result can open the barrier without a `TERMINAL` journal; and a participant-bearing non-manifest route can skip `RECONCILE`.
- Tester additionally found a Medium parser/schema differential for nullable `OPEN/CURRENT_NO_EFFECT.manifest_physical_identity_ref`.
- PMST-I1 is not accepted, not commit-ready and not eligible for native continuation. The DEV-4 two-cycle autonomous review/fix budget is exhausted, so no third implementation correction is started under the present authority. Resume requires an explicit Owner Recovery authorization that preserves this exact responsibility boundary and reopens a bounded correction plus fresh independent review.
- No Windows service, ACL, real Project, native QA, Release, Deploy or Production effect occurred.

## PMST-I1 Recovery R1 authority

On 2026-09-27 the Owner answered `つぎへ` directly to the explicit Recovery authorization request recorded above. This reopens one bounded correction for the four recorded High findings and one Medium parser/schema differential, followed by a fresh independent review. The exact seven Allowed Files and pure-only responsibility boundary are unchanged. Windows service installation, ACL mutation, real Project writes, native QA, Release, Deploy and Production use remain excluded.

Recovery R1 now separates commit and terminal witness revisions, binds journal prior/successor commitments to the pinned OPEN state and exact intent payload, binds committed manifest digest/physical identity to the COMMIT result, binds terminal/readback manifest content, derives query CURRENT/SUPERSEDED from the committed witness plus readback, verifies query witness-state/journal-phase consistency, and requires a validated `TERMINAL` journal before opening the admission barrier. Participant receipts now match exact plan identity, ordered object commitments and phase sequence; all accepted receipt/object observations must be present in the corresponding witness. Participant-bearing non-manifest and unknown-object routes enter RECONCILE before TERMINAL. A manifest operation quarantined before the manifest effect preserves `manifest_commit_observation=NOT_OBSERVED` through its closed terminal result instead of fabricating a manifest attempt. Parser and schema now both reject a null current manifest physical identity.

- Focused PMST-I1: `65 PASS`.
- PMST-I1 plus direct TASK-099 currentness: `87 PASS`.
- Runnable TASK-043 Project / durable Job / history-autosave-backup regression: `66 PASS`.
- `tests/test_task043_project_save_recovery.py` remains `NOT_CONFIRMED` for the already recorded missing WSL `referencing` dependency; no installation was attempted.
- Next gate: fresh independent DEV-4 Critic/Judge and Tester review of the frozen Recovery R1 exact7.

## PMST-I1 Recovery R1 acceptance

- Final frozen source/schema/test correction hashes were source `a0cdce814f970425fa3dcdd76c15e608b4b9ee4a7c1fad0c2e1280b2210f750f`, root/mirror schema `011a17bc6dc27eff81c549f5c03f18e7d80a93f4e50e5bf1415bf1a9bfa7bd3c`, and tests `4eef1c0aa70245e10f86c9b19689998312ee2c55d9e0adcd376346120d38fdba`.
- Independent Critic/Judge: `ACCEPT`, C/H/M/L `0/0/0/0`. Independent Tester: `PASS / ACCEPT`, C/H/M/L `0/0/0/0`. Both matched exact7 and schema mirror and performed no edit, dependency installation, native or external effect.
- Accepted local Evidence is focused `65 PASS`, TASK-102 plus direct TASK-099 `87 PASS`, and runnable TASK-043 Project/Job/History `66 PASS`. The separately recorded save-recovery route remains `NOT_CONFIRMED` only because the existing WSL environment lacks `referencing`; no dependency was installed.
- PMST-I1 is accepted only as a pure protocol/state-machine/fake-port/schema unit. It proves no Windows service, ACL, filesystem CAS/durability, real Project mutation, installer, native QA, Release, Deploy or Production behavior.
- Next unit is PMST-N1 feasibility/native design and requires its own explicit Human Gate; it is not authorized by this acceptance.

## PMST-N1 authority and bounded execution plan — 2026-09-27

The Owner explicitly instructed `TASK-102 PMST-N1を承認` immediately after the bounded Windows Production-foundation proof was described as service/ACL/safe-save/recovery validation in a dedicated temporary root without touching a real Project. This authorizes the PMST-N1 feasibility lane only.

PMST-N1 is decomposed into two ordered native proof units:

1. **PMST-N1A — non-elevated native primitive proof.** Prove unique-Temp containment, local NTFS/topology admission, physical identity, root/control/manifest sharing barriers, staged replacement, file and directory flush, crash-seam witness classification, a protected task-owned DACL, first-instance local named-pipe behavior and server/client PID readback. No service registration or existing path mutation.
2. **PMST-N1B — dedicated service-SID exclusion proof.** Only after N1A PASS and only if an elevated execution route exists. Create one uniquely named temporary test service, bind its service SID to the task-owned control root and pipe, prove ordinary-user mutation rejection plus service-owned mutation, then remove the exact service and task root. Absence of elevation is `NOT_CONFIRMED / BLOCKED_PRIVILEGE`, not a reason to weaken the service-SID design.

Exact Allowed Files for PMST-N1A/N1B implementation and completion synchronization:

1. `docs/ai-team/tasks/TASK-102/task.md`
2. `docs/ai-team/tasks/TASK-102/pmst-n1-windows-feasibility-plan-r0.md`
3. `src/ai_video_production/task102_windows_feasibility.py`
4. `tools/windows/test-task102-pmst-n1.ps1`
5. `tests/test_task102_windows_feasibility.py`
6. bounded Evidence under `docs/ai-team/tasks/TASK-102/evidence/` or the canonical external TASK-102 Evidence root
7. completion-only synchronization in `docs/ai-team/current-state.md` and `docs/ai-team/task-index.md`

Every native run must use one new run-specific directory beneath the OS system temporary root, validate exact physical containment before effects, reject existing/foreign roots, record all resolved roots and residuals, and remove only artifacts created by that run after identity revalidation. Existing Projects, repository content outside Allowed Files, existing services, existing ACLs, private voice/model data, Release, Deploy and Production remain prohibited. PMST-N1 may prove feasibility or a precise unavailable boundary; it may not represent partial proof as Product readiness.

## PMST-N1A result and PMST-N1B boundary — 2026-09-27

PMST-N1A is technically `PASS` on the supported Windows host. Run `20260927-n1a-final-007` proved a unique system-Temp child on fixed NTFS, non-inheritable root/control/manifest barriers with five second-process rejection observations, a DELETE-capable handle-bound same-volume replacement with changed physical identity, file plus directory flush, closed recovery classification across three process-termination seams, a protected and stable task-owned control DACL, and an explicit local named-pipe descriptor with first-instance-specific rejection, remote-client rejection configuration and mutual process-ID readback. Focused TASK-102 tests are `78 PASS` including direct PMST-I1 regression. The native report file SHA-256 is `3eba567cc83001211174f34e06924de91f67cda8a0bcbcd726ca27c44e867692`; the public-safe summary is under this Task's `evidence/` directory.

This is not a physical power-loss proof and creates no Product enrollment or writer authority. PMST-N1B was not executed because both the sandbox and host execution token were non-elevated. No service-create effect was attempted, no existing service or ACL was changed, and the exact result is `NOT_CONFIRMED / BLOCKED_PRIVILEGE`. Therefore PMST-N1 as a whole is not accepted complete and PMST-I2 remains blocked until a separately elevated, exact N1B run proves service-SID exclusion and cleanup.

## PMST-N1B completion — 2026-09-28

The Owner instructed `PMST-N1B再開OK`. The non-elevated controller launched one explicit UAC-elevated bounded runner; no credential capture or bypass occurred. Final run `20260928-n1b-final-007` is `PASS`.

The runner created one random `BvpTask102PmstN1-*` demand-start own-process test service, enabled its unrestricted service SID, and read back the exact registered image command, LocalSystem identity, start mode, process type and SID type before start. The service ran a copied helper inside the operation-owned Machine Temp root. SYSTEM, Administrators and the interactive user had read/execute only; the service SID was the sole Full-control ACE on the protected control directory. The live service token contained the expected service SID and created the closed proof object. The peer controller was denied create, overwrite, delete and directory rename. The explicit protected pipe configuration rejected a second first-instance creator, configured remote-client rejection and proved both service/client PIDs. The exact service stopped and was deleted; post-run service inventory found zero `BvpTask102PmstN1-*` residual services.

The final body-free report file SHA-256 is `deea6770c9499d72319dd022dde6dec6d943432251ff836636f7ad86e573e446`. Exact DACL readback confirmed four explicit non-inherited allow ACEs: service SID Full control and interactive user, SYSTEM and Administrators ReadAndExecute plus Synchronize. N1A regression remained `PASS`; PMST-I1 plus N1 focused tests are `85 PASS`. Earlier N1B recovery runs were preserved rather than hidden: one rejected an invalid empty-password `sc config` form, two proved service cleanup after virtual-account service-start access denial, run 004 established the accepted topology, run 005 added configuration readback, and run 006 exposed and corrected the RX/Synchronize comparison.

PMST-N1 is now technically complete within its stated claim. It proves process-termination recovery and Windows primitive/service-SID feasibility, not physical power-loss durability, Product enrollment, writer migration or Production readiness. PMST-I2 may be proposed as the next unit but remains unauthorized until its own bounded authority is recorded.

## PMST-I2 authority and Atomic Unit plan — 2026-09-29

The Owner explicitly answered `PMST-I2 承認します`. PMST-I2 is therefore authorized only for source/test migration of every accepted D1 writer, recovery and protected-lock route behind a disabled-by-default Product composition. Existing unenrolled Projects retain current behavior. No source-only checkpoint can activate enrollment, install/update the Windows service, change an ACL, write a real Project, run native QA, Release, Deploy or activate Production.

PMST-I2 is decomposed into ordered units so each reaches a reviewed commit-ready boundary:

1. **PMST-I2A — writer migration kernel.** Freeze the accepted D1 matrix digest and all 13 route/profile bindings; admit strict PMST requests only for an exact ACTIVE enrollment and complete matrix; block unknown/old/partial routes and every legacy mutation/lock for any enrolled state; retain read-only compatibility. No current writer is connected in I2A.
2. **PMST-I2B — central manifest/coordinator migration.** Route R001/R002/R011/R012 through the kernel and a closed Product PMST port; keep the legacy path only for a proven unenrolled root; block the legacy journal and direct `_save_unlocked` bypass for enrolled roots.
3. **PMST-I2C — protected object and lock migration.** Route or explicitly feature-block R003 through R010, including Job, history, autosave, backup, VoiceProfile, Timeline recovery, read leases and TASK-029 participant paths.
4. **PMST-I2D — semantic caller/source-policy closure.** Bind every D1 caller to an accepted adapter or deterministic unavailable result and make an unregistered protected-control mutation/lock source fail the source-policy test.
5. **PMST-I2E — integration review and completion.** Run focused, direct-consumer and targeted Project regressions, independent DEV-4 Critic/Tester review, hosted CI and completion Evidence. Enrollment remains disabled until PMST-C is separately authorized.

PMST-I2A exact Allowed Files:

1. `docs/ai-team/tasks/TASK-102/task.md`
2. `docs/ai-team/tasks/TASK-102/pmst-i2-writer-migration-plan-r0.md`
3. `src/ai_video_production/task102_project_writer_migration.py`
4. `tests/test_task102_project_writer_migration.py`
5. bounded Evidence under `docs/ai-team/tasks/TASK-102/evidence/` or the canonical external TASK-102 Evidence root

I2A must not modify existing Product writer/store modules. Its exit requires exact route/matrix/profile binding, strict request/result binding, fail-closed negative tests, unchanged default Product behavior, focused TASK-102 regression, exact Allowed Files verification and external Evidence readback. I2B may not begin until I2A is commit-ready.

## PMST-I2A Builder checkpoint — 2026-09-29

- Added an effect-free writer-migration kernel with the exact accepted matrix record digest, immutable R001 through R013 registry and closed operation-kind/profile bindings.
- The default resolver returns no enrollment and preserves existing unenrolled behavior. Every valid enrolled state blocks legacy mutation/lock access; only exact ACTIVE enrollment plus the complete matrix and a bound port can route a strict I1 request. R013 and unknown routes are always blocked.
- The local Project path remains inside the trusted resolver and is never forwarded to the port. Port results are reparsed and cross-bound to operation, kind, profile, intent and request digests.
- New I2A focused tests: `15 PASS`. PMST-I1/N1/I2A focused regression: `100 PASS`. Python compile and `git diff --check`: `PASS`.
- The Windows Python environment stopped at collection because the pre-existing environment lacks `jsonschema`; no dependency was installed. The established WSL environment executed the tests successfully in unique `/tmp` roots.
- No existing Product writer/store source, real Project, service, ACL, native runtime, private data, Release, Deploy or Production state was changed. PMST-I2B is the next ordered unit after this checkpoint is committed.
- I2A commit: `32f72ab424cb003c1c8faf0c1346588b5e6e32ec`.

## PMST-I2B exact scope — 2026-09-29

Exact Allowed Files:

1. `docs/ai-team/tasks/TASK-102/task.md`
2. `docs/ai-team/tasks/TASK-102/pmst-i2-writer-migration-plan-r0.md`
3. `src/ai_video_production/task102_project_writer_migration.py`
4. `src/ai_video_production/product_project_store.py`
5. `src/ai_video_production/project_save.py`
6. `tests/test_task102_project_writer_migration.py`
7. `tests/test_task102_project_writer_migration_central.py`
8. bounded Evidence under `docs/ai-team/tasks/TASK-102/evidence/` or the canonical external TASK-102 Evidence root

I2B may add explicit injected PMST routing to central manifest create/transition and coordinated save. It must preserve existing unenrolled APIs and semantics. For an enrolled root, it must reject missing/mismatched PMST requests before creating the legacy lock or journal; accept only a strict request routed by I2A; and return success only after canonical manifest plus child readback matches the requested successor. Direct `_save_unlocked` and every legacy complete/rollback/orphan recovery entry must be blocked for enrolled roots. An enrolled recovery status or integrity read without a future exact broker query/read-lease adapter must return a deterministic unavailable error, never inspect the legacy journal as authority or fall back. Product enrollment and native effects remain prohibited.

## PMST-I2B Builder checkpoint — 2026-09-29

- `ProductProjectManifestStore.save` now accepts an explicit injected PMST router/request. It preserves the legacy path for a proven unenrolled root, validates create/transition predecessor and successor semantics before the port call, creates no legacy lock on the PMST path, and returns the existing whole-document `AtomicWriteResult` checksum only after exact canonical readback.
- `ProductProjectSaveCoordinator.save` routes an explicit R002 request without the legacy lock/journal, preserves target/child validation and returns success only after exact manifest and child readback. Participant/commit-guard paths are deterministically unavailable until their closed adapter is added.
- Enrolled direct `_save_unlocked`, legacy save, complete/rollback/orphan recovery are blocked before mutation. Enrolled legacy recovery-status and integrity-read paths require future broker query/read-lease adapters instead of silently consulting the old journal.
- Focused I2A/I2B: `23 PASS`. TASK-102 plus runnable central TASK-043 regression: `145 PASS`. Audio Placement, Timeline Audio, Interactive Timeline and Meter Policy consumer regression: `223 PASS / 1 Windows-only SKIP`.
- `tests/test_task043_project_save_recovery.py` remains `NOT_CONFIRMED` at collection because the established WSL environment lacks the already-declared `referencing` package. No dependency installation was attempted. Equivalent participant/recovery consumer cases initially exposed and then verified the journal-call compatibility correction (`15 PASS`).
- Python compile and `git diff --check`: `PASS`. No real Project, service, ACL, native runtime, private data, Release, Deploy or Production effect occurred.
