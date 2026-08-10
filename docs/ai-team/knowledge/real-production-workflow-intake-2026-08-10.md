# Real Production Workflow Knowledge Intake — 2026-08-10

## Purpose

OwnerがAIを活用して完成まで進めた11資料を、BAI Video Productionの設計入力として分析した記録です。作品固有の台詞、個人情報、職歴、秘密情報を製品既定値へコピーせず、複数制作で再利用できる工程・判断・失敗条件だけを抽出します。

## Source coverage

| Source group | Reusable evidence | Product destination |
|---|---|---|
| 90秒紹介動画3資料 | 全体尺固定、章→Cut、仮ナレーション実尺、SRT、BPM、一本化WAV、既存素材優先 | TASK-006, 014, 022, 026, 027 |
| ブランドムービーMapping | PERSON/SPACE/PROMPT/ASSET/CAMERA/AUDIOの正規ID、未生成予約、旧称移行 | TASK-027 Scene Ledger / Registry |
| マイプロモーション完全制作 | 34 Scene台帳、文字化け失敗、生成Risk A/B/C、Locked参照、構造検査、版管理 | TASK-027, 029 |
| OP/ED Knowledge + Prompt Master | 意味優先の尺削減、Scene別SE同期、最終Hold、生成音声の扱い | TASK-026, 027 |
| Suno Full Mix / Stem Remix | A/B1/B2比較、同一条件評価、アーティファクト、採点、採用理由 | TASK-013, 026, 029 |
| DBD EQ設計2資料 | RAW/処理後比較、波形・スペクトル・聴感、役割別Profile、微調整 | TASK-011, 019, 029 |
| 20-shot PV設計 | Character lock、Start/End、独立VFX plate、Track責務、End Card組版、QA | TASK-004, 010, 027 |

## Promoted reusable rules

1. **Duration-first:** 生成前に全体尺、Scene範囲、無発話区間、End Card Holdを確定する。
2. **Real-first asset policy:** `REAL_CAPTURE → REUSE_EXISTING → COMPOSITE → AI_GENERATED`の順で検討し、AI生成を常に第一候補にしない。
3. **Stable registry:** PERSON、SPACE、PROMPT、ASSET、AUDIOは正式IDを正本とし、未生成項目も`PLANNED`として予約する。
4. **Risk-classified generation:** 文字なし／見出し／密なUIをA/B/Cに分類する。Cは参照画像をLockし、Cameraを固定し、文字を後段組版する。
5. **Narration-measured timing:** 台本文字数ではなく仮音声の実尺、波形、SRT、聴感で尺を確定する。低レベル残留音を完全無音と誤認しない。
6. **Common zero point:** BGM、ナレーション、Sound Logo、映像を共通Timeline原点へ配置し、手作業の細切れ配置を減らす。
7. **Meaning before beat:** 映像とNarrationをBPMへ無理に従属させず、意味構造を優先して小節へ寄せる。
8. **Comparison before adoption:** Full Mix、軽処理Stem、詳細Stemなどを同一ラウドネス・同一区間・複数再生環境で比較し、採用理由を残す。
9. **Generated audio is not automatically canonical:** AI動画に偶発的に付いた音は既定で不採用とし、Audio Planで承認されたSE/BGM/Narrationだけを配置する。
10. **Final hold:** 接続安定性と視認性のためScene末尾またはEnd Cardに明示Holdを設ける。
11. **Security before capture:** 実画面はAPIキー、メール、IP、顧客情報をダミー化・マスクした後に収録する。
12. **Failure is evidence, not truth:** 失敗操作や単発採用を学習ルールへ直結せず、仮説・対照・再修正率・QA・時間・人間採否で評価する。

## Project-specific values not promoted globally

- 固有キャラクター外見、ブランド色、台詞、ロゴ、Scene内容。
- 特定楽曲のBPM、特定EQ周波数・Gain・Limiter値。
- 特定DAWのTrack名やプラグイン名を唯一の実装として固定すること。
- Google Flow、Suno、Cubase等の一時的な画面仕様をCanonical契約にすること。

これらはOwner TemplateまたはProvider Profileとして保存できる候補ですが、製品共通知識にはしません。

## Implemented now

- `ProductionBlueprint` / Scene Ledger契約。
- Timeline全域を隙間・重複なく覆うScene検証。
- Reference Registryと未生成`PLANNED`項目。
- Real-first source strategy。
- A/B/C generation riskと、Risk CのLocked／Static／post-composite hard gate。
- Scene単位のNarration、Dialogue、SE、BGM、Sound Logo計画。
- Scene末尾Holdの明示。

## Routed follow-up

| Follow-up | Task |
|---|---|
| GUIで目的・尺・Scene・Reference・Audioを編集 | TASK-027 Slice A2 |
| 仮ナレーション→実尺→SRT→一本化WAV | TASK-014 + TASK-026 |
| Source Strategy候補と権利・秘密情報Preflight | TASK-003 + TASK-027 |
| Full Mix／Stem候補の正規化比較と採点 | TASK-026 + TASK-029 |
| Character／Space continuity lockとStart/End検査 | TASK-004 + TASK-011 |
| 仮説・比較・Owner採否・Undo／再修正を使う学習 | TASK-029 |

## Privacy decision

原資料はOwner提供の設計Evidenceです。リポジトリへ原文複製せず、この一般化済みIntakeだけをGit管理します。将来Cloud Learningを導入しても、元動画、音声、字幕本文、Prompt、個人情報は既定で送信しません。
