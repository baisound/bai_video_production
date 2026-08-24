# TASK-029 — Human Edit Learning / Federated Knowledge Evolution

- Status: `R0_R1_R2_R3_HOSTED_CLOSED / R4_OWNER_PROFILE_REGISTRY_CANDIDATE_IMPLEMENTED_LOCAL`
- Governance: `DEV-4 PRIVACY, LEARNING AND RELEASE INTEGRITY`

## Owner priority routing — 2026-08-24

The Owner assigned this Task to the current developer lane and moved it ahead of the remaining general Learning & Operations queue. The exact lane order is:

```text
TASK-055 local lane recovery/integration audit
-> TASK-056 final BVP integration
-> TASK-029 Human Edit Learning R0
-> TASK-019 Profile Auto-Tuner hosting/integration
```

This routing authorizes bounded local implementation planning and implementation under DEV-4. It does not by itself authorize private production-data ingestion, Cloud telemetry, automatic Owner Profile or Knowledge Pack promotion, Release, Deploy, or Production effects.
## R0 implementation — canonical Evidence / Decision boundary

R0は、既存Product ownerのadmitted Human Evidenceをbody-freeな
`HumanActionEvidence`へ正規化し、複数記録と6つの独立評価軸から
`OwnerDecisionCandidate`を決定的に作るpure contractを実装する。

- TASK-055 Montage Human Edit Evidenceをexact Proposal/Plan/Evidence lineageでadmitする。
- do-not-learn、即時Undo、後工程再修正を学習対象から除外する。
- Safety/Rights FAILまたはUNKNOWNをHard Gateとして加重点で相殺しない。
- UNKNOWN / STALE / REVOKED / sample不足 / context混在 / axis regressionを別状態で保持する。
- quality、rework、time、QA、Human acceptance、sample confidenceを別軸で保持する。
- raw media、本文、host path、credentialをrecordへ含めない。
- Profile write、Knowledge Pack promotion、Cloud telemetry、rollback、Edit Plan/Timeline、
  Resolve、external effect authorityをすべてfalseに固定する。

R0はfilesystem/database Storeを作らない。Owner Decision Storeのencrypted durable
persistence、Human adoption、Owner-wide Profile、TASK-019 bridge、Cloud、Knowledge Packは
後続のbounded Atomic Unitである。

R0はPR #286でmergeされ、closure PR #288、registry revision 57、post-main CI/Security PASSによりshared CHANGELOG lockを解放済み。

## R1 implementation — encrypted Owner Decision Store

R1は`READY_FOR_HUMAN_REVIEW` Candidateへの明示Human ADOPT/REJECTを、Windows Current User DPAPI既定の暗号化append-only historyへ保存する。cross-process CAS、chain/replay/scope検証、atomic replace、restart read-back、wrong-key/tamper/symlink/power-loss fail-closedを実装する。disk envelopeへOwner scope、Candidate、理由コードを平文保存しない。

R1はOwner Profile write、Knowledge Pack promotion、Cloud telemetry、rollback、plaintext export、physical delete、Timeline/Resolve、external effect authorityを生成しない。retention/purgeはTASK-017、Profile proposalはTASK-019、Profile materializationとPack promotionは後続Unitである。focused R0/R1は`27 PASS`。

R1はtarget PR #289、closure PR #291でhosted closedとなり、shared CHANGELOG reservationを解放済み。

## R2 implementation — pure Owner Profile materialization candidate

R2はhosted closed済みTASK-019 R1のexact Proposal/Owner Decision Bindingと、最新TASK-029 Owner Decision Historyを毎回再検証し、immutableな`OwnerProfileMaterializationCandidate`をin-memoryで決定的に生成する。

- 全adjustmentが相異なる明示ADOPTED decisionへexact bindされたREADY状態だけ、提案済み`ScoringProfile` snapshotを公開する。
- proposal非READYまたはselected REJECTED decisionを別stateに保ち、Profile snapshotを公開しない。
- history/proposal/binding/baseline/proposed/rollback hashとsource decision IDを固定し、payload/source driftをfail closedにする。
- Owner Profile Store、Model/Profile Registry、Knowledge Pack、automatic promotion、rollback execution、Timeline/Resolve、external effect authorityはすべてfalseに固定する。

R2はfilesystem/database/DPAPI/Store I/Oを持たない。target PR #300、closure PR #302、registry revision 66でhosted closedとなった。初回main CIの既存TASK-036 Windows 3.12 multiprocessing試験は固定10秒を超えてFAILしたが、同一commit failed-job再実行で6/6 matrix PASS、Security PASSとなり、shared CHANGELOG reservationを解放済み。

## R3 implementation — explicit-Human-confirmed encrypted Owner Profile Store

R3はR2候補を保存直前にexact sourceから再生成し、別recordの明示Human確認が候補hash、Owner scope、proposed Profile hashへ一致した場合だけ、Owner-local Profile revisionを暗号化appendする。

- Windows Current User DPAPIを既定とし、Owner Decision Storeとは別のentropy domainを使う。
- disk envelopeはciphertextとintegrity metadataだけを持ち、Owner scope、candidate/confirmation ID、Profile snapshotを平文保存しない。
- cross-process lock、expected-revision CAS、append-only hash chain、atomic replace、restart read-backを必須にする。
- 同一Owner scope/Profile identity、previous active Profileと次baselineの連続性、candidate/confirmation/Profile version非replayを検証する。
- wrong-key、tamper、plaintext、symlink、partial writeをfail closedにする。

R3の確認は1回のencrypted Store appendだけを許可する。runtime scoringへの適用、Model/Profile Registry write、Knowledge Pack promotion、automatic promotion、rollback execution、physical delete、Timeline/Resolve、Provider/Cloud、Release/Deployは許可しない。

R3 focused＋直接依存は`36 PASS`、TASK-019/029全体は`61 PASS`、全Product regressionは`3681 PASS / 6 SKIP / 0 FAIL`。target PR #303、lock-host PR #304、closure PR #305がmergeされ、fresh main `797feb073cf50d3a440b070265e2dbed7fc59cad`、registry revision 68、post-main CI/Security PASSでshared CHANGELOG lockを解放済み。

## R4 implementation — pure Owner Profile Registry admission candidate

R4はR3 encrypted Owner Profile Historyのlatest revisionを毎回exact再検証し、TASK-008 `ScoringProfile`へsemantic再構築した上で、Model/Profile Registry登録前のimmutable in-memory候補を生成する。

- history/revision/materialization/confirmation/proposal/binding/decision lineageをhashで固定する。
- callerの`expected_history_revision`とlatest revisionが一致しない場合はstaleとしてfail closedにする。
- rule、modality、weight、source selector、semantic version、Profile hashをTASK-008型で再検証する。
- compatibility contractは`TASK-008/SCORING_PROFILE/1.0.0`へ固定する。
- Owner scopeはbody-free SHA-256 coordinateだけを保持する。

R4はModel/Profile Registry write、runtime scoring apply、Knowledge Pack promotion、automatic promotion、rollback execution、Timeline/Resolve、Provider/Cloud、Release/Deploy authorityを生成しない。別の明示Human registry confirmationと後続Unitが必要である。

R4 focused＋R2/R3直接依存は`23 PASS`、TASK-019/029 chainは`68 PASS`、最終全Product regressionは`3688 PASS / 6 SKIP / 0 FAIL`。compileall、strict Schema validation、schema mirror、diff-checkもPASS。

## Objective

人間の編集作業を盲目的に模倣せず、仮説、反証可能な評価、再現性および複数の品質指標に基づいて、有益と判断された操作だけをOwner Profileまたは製品共通知識へ昇格する。利用頻度に応じて各配布先オーナーへ適応し、明示同意がある場合だけ匿名化統計を製品改善へ利用する。

## Storage boundaries

| Store | Content | Git |
|---|---|---|
| Human Action Evidence | 操作前後、候補、採否、取り消し、作業時間の事実 | No |
| Owner Decision Store | オーナー固有の傾向、仮説、スコア、信頼度 | No; local encrypted by default |
| Optional Cloud Telemetry | 同意済み・最小化・匿名化した特徴量と評価値 | No |
| Dictionary | 固有語、字幕表記、NG語など明示語彙 | SchemaのみGit、値はOwner data |
| Knowledge Pack | 再現性確認済みの一般ルール、重み、適用条件 | Yes; signed and versioned |
| Model/Profile Registry | 昇格済みProfile、互換性、評価Evidence参照 | Metadata/version in Git |

## Learning gate

1. 操作を事実として記録するが、直ちに正解ラベルにしない。
2. `この変更は品質指標Xを条件Cで改善する`という仮説を作る。
3. 自動QA、人間の採否、再修正率、手戻り時間、公開後KPIなどを評価する。
4. ベースライン／対照候補と比較し、効果量、信頼区間、サンプル数を保持する。
5. 誤操作、即時Undo、後工程での再修正、単発外れ値、権利・安全違反を昇格対象から除く。
6. Owner固有の改善と製品共通化可能な改善を分離する。
7. 製品共通知識は複数Owner・複数案件で再現し、Reviewと署名を経てKnowledge Packとしてreleaseする。
8. 新Packは段階適用し、品質低下時は以前のGit versionへrollbackする。

## Real-production hypotheses registered for future evaluation

Owner提供の11制作資料から、次を「正解」ではなく検証対象の初期仮説として登録する。

- 実素材優先は、ブランド信頼性を上げつつ生成コストと再修正を減らす。
- 密な日本語UIをLocked／Static／post-compositeにすると文字化け再生成率が下がる。
- 仮ナレーション実尺からSRTと一本化WAVを作ると手動配置時間と同期ずれが減る。
- Scene末尾HoldはScene間接続の不安定さと視認不足を減らす。
- Full Mix／Stem候補を同条件で比較すると、単一手法固定より採用後の再修正が減る。
- RAW／処理後の比較と複数再生環境評価は、音響処理の過剰適用を減らす。

評価時は動画種別、文字密度、Provider、再生環境を条件として保持し、単一作品の成功だけでKnowledge Packへ昇格しない。

## Scoring model

単一の総合点だけで自動採用しない。候補スコアは少なくとも、品質改善、再修正削減、時間短縮、QA適合、ユーザー採用、権利・安全、サンプル信頼度を別軸で保持する。Safety/Rights違反は加重点で相殺できないHard Gateとする。重みは動画種別とOwner Profileごとにversion管理する。

## Cloud privacy floor

- Cloud learningは初期状態OFFで、目的別の明示Opt-inと撤回を提供する。
- 元動画、音声、画像、字幕本文、Prompt、個人情報、API credentialは既定で送信禁止。
- tenant分離、暗号化、retention、削除要求、export、監査、地域選択を契約化する。
- 少数集合、希少特徴、再識別可能な値は送信または集約結果から除外する。
- Cloud障害や不同意でもOwner-local learningは継続可能にする。

## Dependencies

TASK-003 Evidence/Asset、TASK-007 Cut Plan、TASK-010 Resolve Assembly、TASK-011 QA、TASK-012 Manual Handoff、TASK-019 Profile Auto-TunerおよびTASK-021 Dashboardと接続する。初回基本編集完成を妨げない後続機能とする。
