# TASK-029 R0 Human Edit Learning Design / Critic / Judge

Date: 2026-08-24

Governance: DEV-4 PRIVACY, LEARNING AND RELEASE INTEGRITY

Status: IMPLEMENTED_LOCAL / HOSTING_PENDING

## Atomic Unit

TASK-029 R0は、既存Productが作ったbody-free Human Evidenceを「事実」として受け取り、
Owner-local学習候補へ集約するpure contractである。永続Store、private production data
ingestion、Cloud telemetry、Profile write、Knowledge Pack releaseはこのUnitに含めない。

### Inputs

- TASK-055のadmitted Montage Proposal / Approved Plan / Human Edit Evidence
- owner/project scopeのSHA-256 coordinate
- CURRENT_VALID / UNKNOWN / STALE / REVOKED
- Safety/Rights gate
- 6つの正規化済み評価軸

### Outputs

- Human Action Evidence
  - source Task/record、before/proposed/final snapshot hash
  - action type、condition fingerprint、Human disposition
  - do-not-learn、即時Undo、後工程再修正、Safety/Rights、Evidence validity
  - media/text/path/credentialを含まない
- Owner Decision Candidate
  - 複数Evidenceのexact hash集合
  - 反証可能なhypothesis ID
  - quality、rework、time、QA、Human acceptance、sample confidenceを別軸で保持
  - policy、axis regression、weighted benefit、Human review state

## Responsibility boundaries

- TASK-055はMontage固有Proposal/Plan/Human Evidenceの正本であり続ける。
- TASK-029は汎用Human Action EvidenceとOwner-local Decision Candidateの正本を所有する。
- TASK-019は後続のProfile Tuning Proposal ownerであり、TASK-029のCandidateをProfileへ
  書き込む権限は持たない。
- TASK-017はretention/purge ownerであり、TASK-029 R0は物理削除を行わない。
- TASK-021はDashboard ownerであり、TASK-029 R0はUI/Operationsを追加しない。

## Privacy and effect floor

- raw media、audio、image、subtitle/transcript/prompt本文を受け取らない。
- absolute host path、credential、Provider設定を受け取らない。
- owner/project scopeはhash coordinateのみで、Cloud送信権限を生成しない。
- filesystem、network、database、media、subprocess、Provider APIをimportしない。
- Human reviewが必要で、Profile write、Knowledge Pack promotion、Cloud telemetry、
  rollback、Edit Plan/Timeline/Resolve、external effectの各authorityは常にfalse。

## State model

Human Action Evidenceは次を区別する。

- ELIGIBLE_FOR_EVALUATION
- DO_NOT_LEARN
- IMMEDIATE_UNDO
- LATER_REVISION
- SAFETY_BLOCKED
- RIGHTS_BLOCKED
- UNKNOWN_EVIDENCE
- STALE_OR_REVOKED_EVIDENCE

Owner Decision Candidateは次を区別する。

- READY_FOR_HUMAN_REVIEW
- INSUFFICIENT_EVIDENCE
- EXCLUDED_EVIDENCE_PRESENT
- CONFLICTING_CONTEXT
- UNKNOWN_EVIDENCE
- STALE_OR_REVOKED_EVIDENCE
- SAFETY_OR_RIGHTS_BLOCKED
- AXIS_REGRESSION
- NO_MEASURED_BENEFIT

READY_FOR_HUMAN_REVIEWは採用・保存・昇格authorityではない。

## Failure-mode design

- evidence ID/hash重複、owner scope違い、condition混在はfail closed。
- 全6評価軸がexact 1件ずつ存在しない候補は拒否。
- 単一のweighted benefitが良くても1軸がpolicy capを超えて悪化した場合は
  AXIS_REGRESSION。
- do-not-learn、即時Undo、後工程再修正をsilent dropせず、Candidateを
  EXCLUDED_EVIDENCE_PRESENTへ固定。
- Safety/RightsのFAIL/UNKNOWNは加重点で相殺しない。
- UNKNOWN、STALE、REVOKEDをsample不足と混同しない。
- outer hash、nested policy hash、metric delta、condition fingerprint、
  no-effect flagsの改ざんを検出する。

## Builder / Completeness Critic

Finding: weighted benefitが単一総合点として自動昇格に流用される危険がある。

Correction: 6軸を個別保持し、axis regressionを先に判定する。出力はHuman review候補だけで
automatic promotion/write authorityを持たない。

Finding: TASK-055 Evidenceを別のMontage storeへ複製する危険がある。

Correction: source recordはTASK-055のexact SHA-256へbindし、TASK-029側はbody-freeな
汎用Evidence envelopeだけを作る。Timeline/Proposal/Planの正本を複製しない。

Finding: Owner Decision Storeの「local encrypted by default」を満たさずに平文Storeを
追加する危険がある。

Correction: R0はpure immutable CandidateまででI/Oを持たない。durable encrypted Storeは
鍵・retention・recovery・delete/export contractを持つ別Atomic Unitとする。

Residual Critical/High: 0 / 0

## Tester responsibility

- deterministic hash / immutable dataclass
- TASK-055 exact lineage admission
- JSON Schema / package mirror
- six-axis completeness
- do-not-learn / Undo / later revision
- Safety/Rights hard gate
- UNKNOWN / STALE / REVOKED
- insufficient sample / context conflict / axis regression / no benefit
- nested/outer tamper
- no I/O/provider/effect import surface
- TASK-055/TASK-019 direct regression

## Judge

- canonical responsibility separation: PASS
- privacy/data-minimization floor: PASS
- multi-axis / hard-gate / rollback-safe boundary: PASS
- automatic promotion/write authority absent: PASS
- R0 implementation authorization: OWNER_DIRECTED_IMPLEMENTATION_2026_08_24
- local technical gate: PASS
  - focused TASK-029: 16 PASS
  - TASK-029/TASK-055/TASK-019/OSS direct regression: 47 PASS
  - full repository: 3644 PASS / 5 SKIP / 0 FAIL
  - compileall / Schema mirror / diff-check: PASS
- hosted integration: PENDING

## Deferred Units

- encrypted Owner Decision Store persistence/recovery
- explicit Human adoption/rejection history
- Owner-wide profile materialization
- TASK-019 proposal bridge
- cross-project evaluation
- optional Cloud consent/anonymization/withdrawal
- signed Knowledge Pack promotion and rollback
