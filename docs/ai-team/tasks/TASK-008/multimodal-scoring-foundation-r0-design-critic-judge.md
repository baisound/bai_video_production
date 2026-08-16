# TASK-008 Multimodal Scoring Foundation R0 — Design / Critic / Judge

## Decision

`IMPLEMENT_PROVIDER_NEUTRAL_DATA_ONLY_SCORING_CONTRACT`

既存TASK-007 graphを変更せず、将来のproposal refinementへ渡せる別manifestを作る。TASK-005/006/024のcanonical rowを直接importせず、producer task/contract + manifest/row SHA coordinateとして束ねることで、循環依存とfeature logicの再実装を避ける。

## Contract

1. `ScoringProfile`はcanonical-sorted rule、2 modality以上、weight総和1000。
2. `FeatureRule`はmodality、raw range、DIRECT/INVERSE、required/optional既定値、allowed source selectorを固定。
3. `FeatureProvenance`はproducer task、contract、manifest SHA、row ID/SHA、validityを分離。
4. `CandidateFeatureInput`はTASK-007 Candidate IDとend-exclusive rangeを保持。
5. compilerは整数round-half-up正規化のみを使用し、候補入力順に依存しない。
6. required欠落、UNKNOWN、STALE/REVOKEDはscore `null`。STALE/REVOKEDはUNKNOWNより強いterminal stateとして記録し、両集合を失わない。
7. optional欠落だけがprofileの明示値を使用する。
8. manifestはTASK-007 Edit Plan SHAへbindし、Human review、advisory-only、no-effectを明示する。

## Dependency / import graph

`TASK-005/006/024 canonical row receipts -> TASK-008 FeatureProvenance`

`TASK-007 Edit Plan SHA + Candidate ID/range -> TASK-008 CandidateFeatureInput`

`TASK-008 manifest -> future Human-reviewed TASK-007 proposal refinement / TASK-009/015/019`

Python importは`ids`と`serialization`だけで、TASK-005/006/007/024 module importは0。したがって既存domain logicを複製せず、consumer coordinateとしてのみ結合する。

## Builder / Completeness Critic

- Finding: optional feature欠落時に分母を再正規化すると候補間比較が変動する。
- Correction: weight総和1000を固定し、optional欠落はprofile記録済み0..1000値でのみ埋める。
- Finding: input orderでmanifest bytesが変わり得る。
- Correction: candidate rowsをrange/ID順にsortし、profile rules/source selectorsはconstructorでcanonical orderを要求。

## Security / Authority Critic

- Finding: producer名やmanifest digestだけをcurrent-valid Evidenceへ昇格できる。
- Correction: exact row SHAとclosed validityを別fieldで必須化し、UNKNOWN/STALE/REVOKEDはscore生成0。なおcontract自体は上流Judge authorityを作らない。
- Finding: Pythonの型注釈だけでは文字列`CURRENT_VALID`をenumとしてlaunderできる。
- Correction: modality、polarity、validity、selector、observationを全てruntime実型検証し、文字列やplain row代替をreject。
- Finding: scoringから自動Cutへ権限launderingできる。
- Correction: `REVIEW_REQUIRED`、`ADVISORY_ONLY`、`automatic_edit_plan_mutation_authorized=false`をmanifestに固定。

## Operations / Compatibility Critic

- Finding: float正規化はplatform差を生む。
- Correction: bounded integerとround-half-upのみを使用。
- Finding: OCRが未実装なのにreadyと誤認できる。
- Correction: OCR modalityとproducer Evidenceを分離し、required OCR rowが無い候補はmissingで停止。OCR execution flagは常にfalse。

## Independent Judge

- Deterministic constituent closure: PASS
- Missing/UNKNOWN/current-valid separation: PASS
- Upstream logic duplication: 0
- Media/provider/filesystem/process/network effect: 0
- Human review and downstream authority boundary: CLOSED
- Residual C/H/M: `0/0/0`

`JUDGE=PASS_IMPLEMENTATION_PROVISIONAL_HOSTED_CHECKS_REQUIRED`
