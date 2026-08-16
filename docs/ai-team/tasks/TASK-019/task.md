# TASK-019 Profile Auto-Tuner

- Status: `R0 FOUNDATION IMPLEMENTED / HOSTING PENDING`
- Owner: 開発担当
- Dependency: TASK-008 Multimodal Scoring、TASK-015 YouTube Feedback
- Downstream: Human-reviewed scoring profile promotion and later rollback execution Gates

## R0 scope

R0は、TASK-008 baseline ScoringProfile、TASK-015 aggregate Feedback Snapshot、bounded weight adjustments、current-valid holdout evaluationsをexact bindし、決定的なProfile Tuning Proposalを作るno-effect contractである。

Weight変更は同一feature集合・同一rule metadataを保ち、policyの変更数・絶対delta・holdout sample・改善・単一holdout回帰capを満たす。feedback incomplete、holdout不足、改善不足、回帰、UNKNOWN、STALE/REVOKEDを別状態でfail closedする。baseline profile digestをrollback coordinateとして保持する。

## Boundaries

- `READY_FOR_HUMAN_REVIEW`はpromotion authorityではない。
- Profile store write、TASK-008 profile置換、自動promotion/rollback、Edit Plan/Timeline変更を行わない。
- YouTube API、Credential、filesystem、network、media、provider、subprocessを使わない。
- 実holdout producer、Human decision、profile adoption、Release/Deploy/Productionは別Gate。

## Verification

- exact TASK-008/015 constituent binding
- deterministic weight projection and canonical proposal/hash
- holdout weighted integer evaluation and rollback binding
- incomplete/insufficient/no-gain/regression/UNKNOWN/stale/revoked negative matrix
- schema mirror and no-effect API/import surface
- Critic/Judge residual C/H/M=`0/0/0`
