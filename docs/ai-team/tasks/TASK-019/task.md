# TASK-019 Profile Auto-Tuner

- Status: `R0 HOSTED / R1 TASK-029 DECISION BRIDGE IMPLEMENTED LOCAL HOSTING PENDING`
- Owner: 開発担当
- Dependency: TASK-008 Multimodal Scoring、TASK-015 YouTube Feedback
- Downstream: Human-reviewed scoring profile promotion and later rollback execution Gates

## Owner priority routing — 2026-08-24

The existing R0 no-effect foundation is retained. R0はPR #155で既にmainへmerge済みであり、再ホストしない。R1 Product integrationはTASK-029 R1 encrypted Owner Decision Storeのtyped historyをconsumeし、競合するProfile/Decision Storeを作らない。The priority sequence is `TASK-055 -> TASK-056 -> TASK-029 -> TASK-019`. No automatic Profile promotion or rollback authority is added.

## R0 scope

R0は、TASK-008 baseline ScoringProfile、TASK-015 aggregate Feedback Snapshot、bounded weight adjustments、current-valid holdout evaluationsをexact bindし、決定的なProfile Tuning Proposalを作るno-effect contractである。

Weight変更は同一feature集合・同一rule metadataを保ち、policyの変更数・絶対delta・holdout sample・改善・単一holdout回帰capを満たす。feedback incomplete、holdout不足、改善不足、回帰、UNKNOWN、STALE/REVOKEDを別状態でfail closedする。baseline profile digestをrollback coordinateとして保持する。

## Boundaries

- `READY_FOR_HUMAN_REVIEW`はpromotion authorityではない。
- Profile store write、TASK-008 profile置換、自動promotion/rollback、Edit Plan/Timeline変更を行わない。
- YouTube API、Credential、filesystem、network、media、provider、subprocessを使わない。
- 実holdout producer、Human decision、profile adoption、Release/Deploy/Productionは別Gate。

## R1 scope — TASK-029 Owner Decision bridge

R1はR0 `ProfileTuningProposal`の全adjustmentを、TASK-029 R1 `OwnerDecisionHistory`内の相異なる明示Human decisionへexact bindするpure no-I/O contractである。

- 全adjustment featureをexact 1 support rowで覆い、同じOwner decisionの複数feature再利用を拒否する。
- decision ID、entry/candidate SHA、hypothesis、action、ADOPTED/REJECTED、history revision/SHA、Owner scopeを保持する。
- R0 proposal非READYとTASK-029 REJECTED decisionを別stateでfail closedにする。
- source proposal/history driftはexact recomputation verifierで拒否する。
- latest encrypted historyの再検証を必須にし、binding単体をcurrent authorityとして扱わない。
- Profile materialization/write、Knowledge Pack promotion、automatic promotion、rollback execution、Edit Plan、external effect authorityをすべてfalseに固定する。

R1はOwner Decision Storeをload/writeせず、DPAPI plaintextをexportせず、Profile Registryを作らない。実Profile materialization、Human adoption、Knowledge Pack昇格/rollbackは後続のbounded Atomic Unitである。

## Verification

- exact TASK-008/015 constituent binding
- deterministic weight projection and canonical proposal/hash
- holdout weighted integer evaluation and rollback binding
- incomplete/insufficient/no-gain/regression/UNKNOWN/stale/revoked negative matrix
- schema mirror and no-effect API/import surface
- Critic/Judge residual C/H/M=`0/0/0`
