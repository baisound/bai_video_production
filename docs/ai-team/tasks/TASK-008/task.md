# TASK-008 Multimodal Scoring

- Status: `R0 FOUNDATION IMPLEMENTED / HOSTING PENDING`
- Owner: 開発担当
- Dependency: TASK-007 Candidate Clip Graph、TASK-005 Scene Boundary、TASK-006 Transcript、TASK-024 review-only Cut Candidate
- Downstream: TASK-009、TASK-015、TASK-019、および将来のTASK-007 Edit Plan proposal refinement

## R0 scope

R0は、既存のcanonical feature row座標だけを入力にするprovider-neutral scoring contractである。各候補をTASK-007 Edit Plan SHA、Candidate ID/range、feature producer task/contract、manifest SHA、row ID/SHA、current-valid stateへexact bindし、整数演算だけで0..1000のadvisory scoreを生成する。

Feature profileは少なくとも2 modalityを含み、weight総和をexact 1000とする。required feature欠落、UNKNOWN、STALE、REVOKEDは別状態でfail closedし、scoreを生成しない。optional featureだけがprofile記録済みの既定値を使用できる。

## Boundaries

- OCR producerは現時点でRepositoryに存在しない。OCR modalityはcontract上区別するが、real OCR capabilityやEvidenceを主張しない。
- Feature値・provenanceの真実性は上流current-valid/Judge receiptの責務であり、名前・digestだけで権限を作らない。
- 出力は常に`REVIEW_REQUIRED`かつ`ADVISORY_ONLY`。Cut/KEEP、Edit Plan承認、Timeline mutationを自動実行しない。
- media/path/raw bytes、OCR/FFmpeg/OpenCV/provider/model、filesystem、network、subprocess、callback/runnerを受け取らない。
- Human decision、Release、Deploy、Productionは別Gate。

## Verification

- deterministic canonical manifest/hash
- fixed-point normalization and exact weight arithmetic
- missing/UNKNOWN/stale/revoked/source/modality/range/cap/digest negative matrix
- TASK-005/006/007/024 implementation変更0
- Critic/Judge residual C/H/M=`0/0/0`
