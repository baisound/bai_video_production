# BAI VIDEO PRODUCTION 表側UI設計書
## Prompt Reference Workbench / Start-End Frame Director

- 作成日: 2026-08-14
- 関連: TASK-036 Unified Desktop Editing Shell
- 対象: BAI Video Production Front UI / Product Design / Codex / Development OS
- 目的: Visual Prompt Director V2 が内部で利用する参照入力・固定範囲・変化範囲・開始終了フレーム設計を、一般ユーザーが扱えるUIとして定義する。

---

# 1. UIの役割

このUIは、単なるプロンプト入力欄ではない。役割は次の3つ。

1. **開始画像 / 終了画像の設計補助**
2. **人物・背景・構図の参照固定**
3. **内部テンプレートへの安全な構造化入力**

つまり、ユーザーは自然言語の長文を頑張って書くのではなく、

- 誰か
- どこか
- 何の途中か
- 直前に何をしていたか
- 何を固定したいか
- 何だけ変えたいか

を UI 上で入力する。

---

# 2. UIの配置方針

## 2.1 設置場所

TASK-036 の Unified Desktop Editing Shell 内に、以下の2か所から開ける。

### A. Scene Inspector から開く

- Scene を選択
- 右側 Inspector に `Start / End Frame` セクション表示
- `Open Prompt Workbench` ボタンで詳細画面へ

### B. Production Control から開く

- Plan → Scene → Asset Slot
- `START_IMAGE` or `END_IMAGE` Slot を選択
- `Generate Candidate` で Workbench を開く

---

# 3. 画面構成

## 3.1 全体レイアウト

```text
┌──────────────────────────────────────────────────────────────────┐
│ Prompt Reference Workbench                                       │
├───────────────────────┬───────────────────────────┬──────────────┤
│ Left: Input Sections  │ Center: Preview / Pair    │ Right: Audit │
│                       │                           │ and Contract  │
│ - Scene Summary       │ - Start Frame Preview     │ - Lock Rules  │
│ - Subject             │ - End Frame Preview       │ - Continuity  │
│ - Space               │ - Before / After Diff     │ - Prompt Out  │
│ - Action Flow         │ - Ref Overlay             │ - Validation  │
│ - References          │                           │                │
│ - Locks & Variation   │                           │                │
└───────────────────────┴───────────────────────────┴──────────────┘
```

---

# 4. 入力セクション設計

## 4.1 Scene Summary

### 表示項目
- Plan ID
- Scene ID
- Slot Type (`START_IMAGE` / `END_IMAGE` / `PAIR`)
- Scene Purpose
- Continuity Group

### 入力項目
- `Scene Theme`
- `Short Intent`
- `Target Use`（動画開始 / 動画終了 / 中間カット / サムネ補助）

---

## 4.2 Subject セクション

### 入力項目
- `Who is the subject?`
- `Age / gender impression`
- `Role / occupation / identity`
- `Body build`
- `Face / hair notes`
- `Wardrobe summary`
- `Recurring personal items`

### UI部品
- Text field
- Tag chips
- Optional `Import from Character Contract`

### 内部マッピング
- `[SUBJECT_IDENTITY]`
- `[WARDROBE_DESCRIPTION]`
- `[OWNED_OBJECTS]`
- `[IDENTITY_LOCK_SCOPE]`

---

## 4.3 Space セクション

### 入力項目
- `Where is the subject?`
- `Room / environment type`
- `Spatial structure`
- `Visible background elements`
- `Off-screen context`
- `Lighting source`
- `Camera family`

### 内部マッピング
- `[LOCATION_TYPE / SPACE_STRUCTURE]`
- `[SPACE_DETAILS]`
- `[VISIBLE_BACKGROUND_ELEMENTS]`
- `[OFFSCREEN_CONTEXT]`
- `[LIGHT_SOURCES_AND_DIRECTION]`
- `[CAMERA_HEIGHT_AND_DISTANCE]`
- `[LENS_DESCRIPTION]`

---

## 4.4 Action Flow セクション

### 4ブロック構成
- `Before`
- `Now (Start Frame)`
- `Action Result`
- `After`

### 入力項目
- `What was happening just before?`
- `What is happening now?`
- `What will happen next?`
- `What physical traces remain?`

### 内部マッピング
- `[BEFORE_ACTION]`
- `[NOW_ACTION]`
- `[ACTION_TRACES]`
- `[NEXT_EXPECTED_MOTION]`
- `[COMPLETED_ACTION]`
- `[NOW_ACTION_AFTER]`
- `[ACTION_RESULT_TRACES]`
- `[NEXT_AFTER_ACTION]`

---

## 4.5 References セクション

### 目的
参照してね領域を、ユーザーに分かりやすい形で明示する。

### 参照スロット
- `Reference A: Subject`
- `Reference B: Environment`
- `Reference C: Wardrobe / Props`
- `Reference D: Composition`
- `Reference E: Continuity / Previous Frame`
- `Reference F: Extra`

### 各スロットのUI
- Upload / Select Asset
- Preview thumbnail
- Role dropdown
- Strictness slider (`Soft / Medium / Strict`)
- Notes field (`what to keep`)

### 内部マッピング
- `[REFERENCE_IMAGE_A_ROLE]` 〜 `[REFERENCE_IMAGE_F_ROLE]`
- `[REFERENCE_PRIORITY_ORDER]`
- `[REFERENCE_USAGE_POLICY]`

---

## 4.6 Locks & Variation セクション

### 入力ブロック
- `Identity Lock`
- `Environment Lock`
- `Continuity Lock`
- `Allowed Variation`

### UI案
- Checkboxes for common lock items
- Freeform extension text
- Presets:
  - `Keep subject identity`
  - `Keep same room`
  - `Keep same outfit`
  - `Allow pose change`
  - `Allow object movement`
  - `Allow light shift`

### 内部マッピング
- `[IDENTITY_LOCK_SCOPE]`
- `[ENVIRONMENT_LOCK_SCOPE]`
- `[CONTINUITY_LOCK_SCOPE]`
- `[ALLOWED_VARIATION_SCOPE]`

---

# 5. 中央プレビュー領域

## 5.1 Dual Preview

- 左: Start Frame Preview
- 右: End Frame Preview
- 中央差分表示: `Diff Hints`

### 機能
- Show paired preview
- Highlight changed items
- Overlay reference image
- Compare with previous scene end frame

## 5.2 Continuity Strip

小さなサムネイル帯で、

`Prev End → Current Start → Current End → Next Start`

を見せる。

---

# 6. 右側 Audit / Contract 領域

## 6.1 Validation Cards

- `World Integrity`
- `Trace Physics`
- `Owner Specificity`
- `Frame Economy`
- `Reference Completeness`
- `Start-End Continuity`

### 状態
- PASS
- WARNING
- FAIL

## 6.2 Internal Prompt Preview

ユーザーには全文を常時見せなくてもよいが、`Advanced` で開ける。

表示内容:
- Generated Start Prompt
- Generated End Prompt
- Template Version
- Filled Placeholder Summary

---

# 7. ユーザーフロー

## 7.1 通常フロー

1. Scene を選択
2. `Generate Start/End Frames` を押す
3. Workbench を開く
4. Subject / Space / Action Flow を入力
5. 参照画像を入れる
6. Lock / Variation を設定
7. `Build Prompt Pair` を押す
8. Internal validation 実行
9. Preview 生成
10. Candidate として保存
11. Audit へ送る

## 7.2 既存参照からの継続フロー

1. 前カットの End Frame を continuity 参照へ自動装填
2. Subject / Environment を自動継承
3. 今回シーンの差分だけ入力
4. Start/End ペア生成

---

# 8. 既定値 / プリセット

## 8.1 Preset: Lifestyle Photo
- 強めの WORLD / TRACE / OWNER
- 中程度の Composition Lock

## 8.2 Preset: Creator Desk / Streamer Room
- Subject Lock 強め
- Environment Lock 強め
- Object Placement 厳密

## 8.3 Preset: Start-End Motion Pair
- Continuity Lock 最優先
- Allowed Variation は pose / gaze / object state 中心

---

# 9. 実装レベルの内部データモデル案

```json
{
  "scene_id": "SC-001",
  "slot_type": "PAIR",
  "template_version": "VISUAL_PROMPT_DIRECTOR_V2",
  "subject": {
    "identity": "...",
    "wardrobe": "...",
    "owned_objects": ["..."]
  },
  "space": {
    "location_type": "...",
    "space_details": "...",
    "visible_background": "...",
    "offscreen_context": "...",
    "light": "...",
    "camera": "..."
  },
  "action_flow": {
    "before": "...",
    "start_now": "...",
    "start_trace": "...",
    "next_motion": "...",
    "completed_action": "...",
    "end_now": "...",
    "end_trace": "...",
    "after": "..."
  },
  "references": [
    {"slot": "A", "role": "subject", "asset_id": "...", "strictness": "strict"},
    {"slot": "B", "role": "environment", "asset_id": "...", "strictness": "strict"}
  ],
  "locks": {
    "identity": "...",
    "environment": "...",
    "continuity": "...",
    "variation": "..."
  }
}
```

---

# 10. UX上の重要原則

1. ユーザーへ `[PLACEHOLDER_NAME]` を見せすぎない
2. 「参照画像の役割」を必ず選ばせる
3. 生成前に、何が固定され何が変わるかを要約表示する
4. 開始画像と終了画像を別々でなくペアとして扱う
5. `AIっぽくしない` のような抽象文は入力補助に使わない

---

# 11. 最終結論

このUIは、内部の複雑な Visual Prompt Director V2 を、一般ユーザーには

- 誰
- どこ
- 何の途中
- 何を固定
- 何を変える

という操作へ翻訳する役割を持つ。TASK-036 系の表側UIに組み込むことで、開始画像 / 終了画像生成の品質と再現性を大きく高められる。
