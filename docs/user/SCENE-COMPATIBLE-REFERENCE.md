# Scene-Compatible Reference — 生成画像・動画の参照画像ルール

BAI Video Production で人物入りのAI画像・動画を作るときは、人物と部屋の「同一性」だけでなく、**そのシーンがそのカメラ位置で物理的に成立すること**を確認します。

## 基本

- 人物: Character / Omni Reference
- シーン構図: Scene専用 Room / Shot Reference
- Style Reference: 色・質感用途。部屋形状固定には使わない
- DIRECT_CONTINUATION: 前シーン End Frame を次シーン Start Frame として同一ファイル再利用

## やってはいけないこと

- 部屋全体の Overview を、そのまま全シーンの本編参照に使う
- 複数方向の部屋画像を渡せばAIが正確な3D空間を覚えると期待する
- 人物の顔を見せるために新しい机や家具をAIに作らせる
- Style Reference だけで部屋配置を固定しようとする
- 連続シーンの境界画像を「似た画像」として再生成する
- Scene ID、字幕、QA説明などを本編生成画像に焼き込む

## Start Frame 前チェック

1. 人物を置く実在位置がある
2. 顔向きとカメラ位置が矛盾しない
3. 必要なものを既存家具のまま同時に見せられる
4. 新しい机・棚・窓・ドア等を足す必要がない
5. Room / Shot Reference が本番カメラに近い

成立しない場合は Prompt を強くするのではなく、**同じ部屋の家具配置を維持した Scene専用 Room / Shot Reference を先に作り直します。**

詳しいProduct設計は:

- `docs/ai-team/knowledge/BVP-KNOWLEDGE-REFIMG-001-scene-compatible-reference-image-rule.md`
- `docs/ai-team/tasks/TASK-013/scene-compatible-reference-gate-detailed-design.md`
