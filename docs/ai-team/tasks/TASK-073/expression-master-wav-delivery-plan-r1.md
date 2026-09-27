# Expression Master WAV delivery plan R1 — TASK-102 dependency allocation

## 1. Revision authority and preserved history

- Project: BAI VIDEO PRODUCTION; coordinator: TASK-073.
- Atomic Unit: `EXPRESSION-MASTER-WAV-PLAN-R1-TASK102-ALLOCATION`.
- Date: 2026-09-27.
- Current branch baseline before this revision: `ad4afbbbab4cab243b93060356cc0592d0b1d08b`.
- Preserved accepted R0 plan SHA-256: `aa7a8e14056085b0daba20f15264a93cf0a184961f1fc602290e56a0fbe030b6`.
- Preserved accepted R0 ledger SHA-256: `7e5541bd5b26a233d535a239b356d9f0edfd827aae4680e302660a50482fd2e4`.
- Authority: the Owner answered `つぎへ` directly to the explicit JCV-N-D Human Gate asking whether to accept the service-SID Secure Project Manifest Transaction Broker and allocate one new direct dependency Task.
- Scope: Task allocation, design, responsibility/count synchronization and review only. Source, service, ACL, enrollment, native, private media/model, Release, Deploy and Production effects remain unauthorized.

R0 and its independent review remain immutable evidence. R1 records a new fact learned during accepted TASK-099 JCV-N detailed design: the legacy TASK-043 pathname store and TASK-068 immutable-only primitive cannot provide secure mutable manifest CAS against an uncooperative same-user writer. Protecting `.bai-project` affects every Project manifest writer and recovery route, so the generic mechanism cannot be hidden inside TASK-099.

## 2. Formal remaining count revision

The formal remaining count is now **18 distinct Task responsibility lanes**:

- 10 direct outcome owners;
- 6 shared platform owners, adding TASK-102 to the prior five;
- 2 connection successors, TASK-099 and TASK-100.

This is **14 existing + 4 new design allocations**. TASK-102 adds one real generic platform responsibility; it does not replace TASK-068, because TASK-068 remains immutable publication/readback while TASK-102 owns mutable canonical Project-manifest transactions. No completed lane is reopened or double-counted. A future reduction requires exact completion/readback evidence and a new current revision; the accepted R0 count remains historically correct for its information set.

## 3. TASK-102 allocation

TASK-102 is the first unused Task ID after the already allocated TASK-100 and TASK-101. It owns:

- generic service/client/enrollment protocol for the existing canonical `.bai-project/project.json`;
- protected owner/DACL and long-lived sharing-barrier topology;
- exact predecessor-CAS and non-selector durable same-operation witnesses;
- restart recovery and root quarantine on ambiguity;
- migration of every canonical manifest mutation/journal/recovery route;
- deterministic read-only rejection of old or unmigrated writers.

It does not own caller semantic transitions, Project schema, Job/Asset/Timeline/voice state, TASK-099 currentness, TASK-068 immutable generation semantics, private voice/model custody or Product authorization. No Project may be partially enrolled.

## 4. Updated dependency order

The only critical graph change is:

```text
TASK-102 PMST-D0 inventory/design
→ PMST-D1 protocol/journal/witness design
→ PMST-I1 pure fake service/client
→ separately authorized PMST-N1 Windows feasibility
→ full manifest-writer/recovery migration
→ TASK-099 JCV-N native adapter
→ TASK-074 live route / TASK-076 live Job
→ real expression Master WAV
```

TASK-099 JCV-I remains accepted and does not wait for TASK-102. TASK-100 and TASK-101 independent design/pure work do not wait for TASK-102. Existing TASK-048/TASK-041/TASK-014/TASK-075 synthetic work also remains independently schedulable under its own authority. Only native selected-head/currentness consumers are blocked by TASK-102 native acceptance and complete writer migration.

Milestone M1 now includes TASK-102 protocol/migration design. M2 adds TASK-102 native proof and complete writer routing before TASK-099 JCV-N native acceptance. M3–M7 retain the R0 meaning.

## 5. Current result and next unit

- TASK-099 JCV-I: accepted complete at commit `32c5badb1b354902754c54427fdfb2080b4cbe32`.
- TASK-099 JCV-N-D R1: accepted by independent Critic/Judge and Tester with C/H/M/L `0/0/0/0`; design commit `ad4afbbbab4cab243b93060356cc0592d0b1d08b`.
- TASK-102 PMST-D0 R1: independently accepted with final Critic/Judge and Tester C/H/M/L `0/0/0/0`; PMST-D1 pure protocol/migration-matrix design is next.
- Windows secure CAS/durability/service/ACL feasibility: `NOT_CONFIRMED`.
- Real expression Master WAV result: `NOT_CONFIRMED`.

Next safe unit is TASK-102 PMST-D1 pure protocol/journal/witness and complete physical mutation/migration-matrix design. D0 acceptance does not authorize implementation or native effects.
