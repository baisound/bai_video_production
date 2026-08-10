# TASK-029 — Human Edit Learning / Federated Knowledge Evolution

- Status: `PROPOSED / OWNER-DIRECTED DESIGN`
- Governance candidate: `DEV-4 PRIVACY, LEARNING AND RELEASE INTEGRITY`

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
