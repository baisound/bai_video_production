# TASK-102 — Secure Project Manifest Transaction Broker

- Status: `PMST_D0_R1_DESIGN_ACCEPTED / PMST_D1_RECOVERY_R1_DESIGN_ACCEPTED / PMST_I1_REQUIRES_FRESH_ALLOWED_FILES / SOURCE_NATIVE_NOT_AUTHORIZED`.
- Governance: `DEV-4 FOUNDATION CRITICAL`.
- Allocation authority: on 2026-09-27 the Owner answered `つぎへ` directly to the explicit JCV-N-D Human Gate asking whether to accept the service-SID broker architecture and allocate one new direct dependency Task. This records acceptance of allocation/design only.
- Responsibility predecessor: TASK-043 remains hosted-closed historical Project schema/store foundation and is not reopened.
- Direct consumer: TASK-099 JCV-N.
- Related dependency: TASK-068 immutable publication/readback remains independently owned and is not absorbed.
- First unused Task-ID audit: `TASK-102` is absent while TASK-100 and TASK-101 are already allocated in this worktree.
- Current implementation authority: none. Service installation, ACL mutation, enrollment, native QA and Product integration remain separate gates.

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
