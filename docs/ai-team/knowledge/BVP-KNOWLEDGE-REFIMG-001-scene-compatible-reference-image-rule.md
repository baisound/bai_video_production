# BVP-KNOWLEDGE-REFIMG-001 — シーン適合型参照画像 設計規約

- Knowledge ID: `BVP-KNOWLEDGE-REFIMG-001`
- Name: `Scene-Compatible Reference Image Design Rule`
- Source: BAI Video Production Product Promotion Team
- Source date: `2026-08-12`
- Product status: `FORMALLY_REGISTERED_PRODUCT_DESIGN_KNOWLEDGE`
- Implementation owner: `TASK-013 — AI SE / BGM / Video Orchestration`
- Runtime foundation: `TASK-004 — Local Visual/Audio AI Runtime Foundation`
- Implementation authorization by this document: `NONE`
- Scope: Product Promo / Corporate / YouTube / Short Ad / AI Video

## 1. 一文で覚えるルール

「同じ部屋の画像」では足りない。AIに渡す部屋画像は、**そのシーンの人物・動作・カメラが、家具を増やさず物理的に成立する画像**でなければならない。

## 2. 発見された失敗

プロモーション動画 P01 系の試行で、Room Overview を Image Prompt、人物 Master を Omni Reference として生成したところ、人物同一性は近づいた一方で、AI が新しい机や別レイアウトを生成した。

根本原因は、人物の要求と Room Overview の撮影アングルが物理的に両立していなかったことにある。

例:

- Room Overview の視線順が「カメラ → 椅子の背面 → 人物座席 → モニター」だった。
- 本編要求は「人物の顔 + ノート + 既存デスク + モニター」を同時に見せることだった。
- 同じカメラ位置では両立しないため、生成AIが机・椅子・人物位置を再解釈した。

## 3. 根本原則

### 3.1 Room Overview は 3D Memory ではない

複数方向の Room Overview を用意しても、生成AI内部に厳密な固定3D空間が成立したとはみなさない。

Room Overview は人間の設計資料、部屋の把握、Scene専用 Shot Reference を作る上流資料には使えるが、対象Sceneのカメラ・人物方向・アクションと両立しない Overview をそのまま本編 Image Prompt にしてはならない。

### 3.2 Reference の責務を分離する

| Role | Reference | Responsibility |
|---|---|---|
| Character Identity | Omni / Character Identity Reference | 顔、髪、年齢感、体格、衣装など |
| Scene Space / Composition | Scene-Compatible Room / Shot Reference as Image Prompt | 机、モニター、座席、カメラ方向、可視範囲 |
| Color / Texture / Tone | Style Reference (optional) | 色、質感、撮影トーン |
| Continuity | Previous End Frame | DIRECT_CONTINUATION 時の厳密な境界継承 |

Style Reference を Room Geometry 固定手段として扱わない。

## 4. MUST

1. Scene ごとに物理的に成立する Room / Shot Reference を用意する。
2. 人物 Identity と Scene Composition の参照責務を分離する。
3. Start / End Frame 生成前に Shot Feasibility を判定する。
4. 人物を置く実在位置が参照画像内に存在することを確認する。
5. 要求する顔向きとカメラ位置が矛盾しないことを確認する。
6. 必要要素を家具追加なしで同時に見せられることを確認する。
7. 既存デスク・モニター・マイク・カメラ・窓・ドア・棚を動かさず成立させる。
8. Room / Shot Reference が本編の最終カメラに十分近いことを確認する。
9. 人物なし Room / Shot Reference を先に確定し、その後 Character Reference を投入することを基本とする。
10. DIRECT_CONTINUATION では前 Scene End Frame を次 Scene Start Frame として同一 Asset / 同一 bytes で再利用する。
11. 本編生成画像と Scene ID / Timecode / QA / Narration Text / Design Overlay を分離する。

## 5. MUST NOT

1. Room Overview をそのまま本編ショットの Image Prompt に流用する。
2. 複数 Room Overview を渡せばAIが正確な3D空間を再構築すると期待する。
3. Style Reference で部屋形状まで固定できるとみなす。
4. 矛盾したカメラ要求を Prompt 文だけでAIに解決させる。
5. 人物を見せるために新しい机・棚・窓・ドアを追加させる。
6. 家具を90度回転、移動、複製することで辻褄を合わせさせる。
7. DIRECT_CONTINUATION 境界を「似た画像」として再生成する。
8. Scene番号、QA説明、字幕、ナレーション文字を本編生成画像へ焼き込む。

## 6. Scene Reference Metadata

最低限、次を Canonical Scene Reference Metadata として扱う。

| Field | Example | Meaning |
|---|---|---|
| `SCENE_ID` | `P01` | 本編 Scene ID |
| `CONTINUITY_TYPE` | `CUT` / `DIRECT_CONTINUATION` | 新規 Start が必要か |
| `CHARACTER_REFERENCE` | `C01_FRONT_MASTER` | 人物同一性 |
| `ROOM_IMAGE_PROMPT` | `P01_ROOM_REF` | その Scene の物理構図 |
| `STYLE_REFERENCE` | `None` | 任意。Geometry authority ではない |
| `REQUIRED_VISIBLE` | `Face, Notebook, Monitor` | 同時に画面へ存在すべき要素 |
| `SUBJECT_ORIENTATION` | `3/4 front to camera` | 人物方向 |
| `CAMERA_POSITION` | `desk front-left 35deg` | 部屋に対するカメラ |
| `START_FRAME_SOURCE` | `NEW` / `PREV_END` | 生成か継承か |
| `PROHIBITED_CHANGES` | `No new desk / no furniture move` | AI に許可しない変更 |

Product implementation では provider-neutral contract とし、特定プロバイダの語彙へ固定しない。

## 7. Generation Gate

Start Frame を作る前に以下を判定する。

### PASS criteria

- 人物を参照画像内の実在位置へ配置できる。
- 要求する顔向きとカメラ位置が矛盾しない。
- `REQUIRED_VISIBLE` を既存家具のまま同時に見せられる。
- `PROHIBITED_CHANGES` に抵触する追加・移動・回転を必要としない。
- Room Image Prompt が Scene の最終カメラに近い。
- Reference role が分離されている。
- DIRECT_CONTINUATION の場合は前 End の exact Asset が存在する。

### FAIL criteria

- 「この部屋を参考に人物を正面に」のように、物理矛盾を生成AIへ丸投げしている。
- Room Overview と Scene camera が不整合。
- 顔・手元・UI 等の同時可視に新規家具が必要。
- Style Reference だけで Geometry を固定しようとしている。
- DIRECT_CONTINUATION なのに Start を再生成しようとしている。

## 8. Standard Workflow

1. PRODUCT / MESSAGE LOCK
2. CHARACTER CONTINUITY LOCK
3. ROOM / SPACE MASTER LOCK
4. SHOT FEASIBILITY CHECK
5. SCENE-COMPATIBLE ROOM / SHOT REFERENCE
6. SCENE ASSET MATRIX
7. START FRAME
8. END FRAME
9. AI VIDEO
10. EDIT / OVERLAY
11. QA

## 9. Continuity Rule

`DIRECT_CONTINUATION` は画像類似ではなく Asset continuity として扱う。

- `next.start_frame_asset_id == previous.end_frame_asset_id`
- SHA-256 も同一であること。
- 再生成、upscale、再encode による別 bytes への置換を継承扱いしない。
- 別加工が必要なら continuity type を明示的に変更して別 Scene boundary とする。

## 10. Knowledge provenance

発見源: BAI Video Production プロモーション動画 P01〜P03 の参照画像生成試行。

Rejected Pattern:
`CHARACTER_LOCK_PLUS_ROOM_OVERVIEW_WITHOUT_SHOT_FEASIBILITY`

恒久対策:
`Scene-Compatible Room / Shot Reference + Shot Feasibility Gate`

この記録は Product 内の設計 Knowledge であり、BAI Development OS の Canonical Knowledge を直接宣言しない。将来 Knowledge Hub / Development OS へ渡す場合も、Product provenance を保持した Candidate として扱う。
