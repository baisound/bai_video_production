# BAI Visual Prompt Director 標準指示書 Ver.2.0
## AI動画生成用 Start Frame / End Frame・参照画像・表側UI 統合仕様

- 文書種別: 新規標準指示書
- 適用先: BAI Development OS / BAI Video Production / Codex / Visual Prompt Generation Pipeline
- 作成日: 2026-08-14
- 状態: DESIGN / IMPLEMENTATION INSTRUCTION
- 旧文書への扱い: 本書は差分パッチではなく、今後の実装・設計・レビュー時に単独で読める新しい正本候補として作成する。

---

# 1. 目的

本仕様の目的は、AI動画生成で使用する**開始画像（Start Frame）と終了画像（End Frame）**を、単なる「きれいな一枚絵」として生成するのではなく、人物・空間・所有物・時間・行動・物理・撮影理由まで一貫した世界の一部として生成できるようにすることである。

特に人物を含む画像では、

> 「それらしい背景に人物を置く」

という作り方を禁止し、

> 人物の生活、行動、習慣、所有物、身体状態、直前の時間、直後の時間の結果として現在の画面が存在する

という設計原則を採用する。

さらに、人物・風景・部屋・衣装・小物・構図などを固定したい場合に、**入力ソースを明示的に参照させるためのReference領域**を標準テンプレート内に確保する。

最終的には、BAI Video Productionの表側UIからユーザーが簡単に入力した内容を、内部で本仕様の構造化Promptへ変換する。

---

# 2. 適用範囲

本仕様は以下に適用する。

- AI動画生成用 Start Frame
- AI動画生成用 End Frame
- Start / End ペア生成
- 人物ライフスタイル画像
- 配信者・クリエイターの生活空間画像
- 店舗・職場・作業空間に人物がいる画像
- Scene間の人物・空間・衣装・所有物の継続性が必要な画像
- 参照人物画像、参照背景画像、参照構図画像が与えられる画像生成
- BAI Video ProductionのScene Asset生成

以下には弱適用または対象外とする。

- 完全抽象映像
- UIモックアップのみ
- ロゴ単体
- 商品切り抜きパックショット
- 人物や空間の継続性を必要としない純粋なグラフィック生成

---

# 3. 最上位原則

## 3.1 人物を世界に置かない

人物を世界に配置するのではない。

人物の行動、習慣、生活動線、所有物、身体状態、直前行動の結果として、現在の世界と画面を作る。

---

## 3.2 背景・小物を雰囲気のために足さない

背景、小物、服、汚れ、シワ、散らかりを「生活感を出すため」「雰囲気を良くするため」という理由だけで追加してはいけない。

可視要素には原則として以下が必要である。

- WHY: なぜ存在するのか
- WHERE: なぜその位置にあるのか
- OWNER: 誰の物なのか

説明できないものは削除する。

---

## 3.3 世界は100%設計するが100%写さない

空間全体を設計しても、画面内には必要部分しか写さない。

以下を積極的に用いる。

- フレームアウト
- 遮蔽
- 暗部
- ボケ
- 奥行き
- 部分表示
- 画面外の人・物・音・光

世界説明図のように全要素を画面へ詰め込んではならない。

---

## 3.4 抽象語を視覚事実へ変換する

以下のような語は、最終Promptへできるだけ入れない。

- 生活感がある
- 本当に暮らしているように
- AIっぽくしない
- 作り込みすぎない
- 広告写真ではない
- 観光客ではない
- リアルな雰囲気

これらは必ず、

- 髪
- 肌
- シワ
- 姿勢
- 手
- 視線
- 残量
- 道具の位置
- 光の落ち方
- カメラ距離

などの具体的な視覚情報へ変換する。

---

# 4. 内部設計手順

ユーザーへ最終Promptを出す前に、内部では以下を順に設計する。

## 4.1 WORLD

人物が普段どんな生活をしているかを決める。

考慮要素:

- 年齢
- 仕事
- 生活時間帯
- 住居/職場
- 所得感
- 趣味
- 物の選び方
- 整理整頓傾向
- 使用頻度
- 家族/同居人
- 身体サイズ

---

## 4.2 BEFORE

写真の少し前まで何をしていたかを決める。

例:

- 配信開始前にOBSやゲームを確認していた
- 庭仕事をしていた
- コーヒーを飲みながら資料を読んでいた
- 調理中だった

---

## 4.3 NOW

現在、何をしている途中なのかを決める。

人物には**カメラとは無関係の目的**を持たせる。

カメラ目線やポーズは、撮影目的から必然性がある場合のみ使う。

---

## 4.4 TRACE

直前までの行動から残る物理的痕跡を決める。

例:

- 長時間座っていた → 腰・膝・肘周辺の座りジワ
- 庭仕事 → 袖の捲れ、湿気で乱れた髪、使用済み道具
- 飲食 → 飲み物の残量、食器の位置
- ゲーム配信 → 握られたコントローラー、姿勢、机上の使用中機材

---

## 4.5 PHYSICS

痕跡や物体位置を、

- 身体位置
- 動作方向
- 重力
- 接触
- 使用順

から決める。

「なんとなくそこにある」を禁止する。

---

## 4.6 PLACE

物を現実の生活動線に従って配置する。

例:

- 食事用品 → 食卓
- 調理用品 → 調理台
- 屋外靴 → 玄関/土間
- 作業道具 → 作業場所
- 頻繁に使うもの → 手が届く位置

生活小物を一つの机へ無差別に集めてはいけない。

---

## 4.7 OWNER

服、小物、靴、器、バッグ、機材などをカテゴリ名で終わらせない。

人物の

- 年齢
- 身体サイズ
- 生活
- 好み
- 経済感覚
- 色選択
- 使用頻度

に合った私物として定義する。

悪い例:

> ガーデニングシューズ

良い例:

> 小ぶりなオリーブグレーのラバー製ガーデンクロッグ

---

## 4.8 SUBJECT

人物自身にも過去の時間を残す。

対象:

- 髪
- 肌
- 袖
- 裾
- シワ
- 姿勢
- 手
- 指
- 表情
- 視線

---

## 4.9 SPACE

部屋、家、店舗、配信部屋、職場等の構造を考え、生活動線と矛盾しないようにする。

---

## 4.10 OFF-SCREEN

画面外に誰がいるか、何があるかを決める。

視線や身体の向きに理由を持たせる。

---

## 4.11 CAMERA

撮影者を実在する一人の人物として設計する。

決めるもの:

- 誰が撮ったか
- なぜ撮ったか
- どこから撮ったか
- どの高さか
- どの距離か
- どんな姿勢か
- どんなレンズ/機材か

その結果としてカメラ位置・画角・露出を決める。

---

## 4.12 LIGHT

光源を実際の空間から決める。

自然光であれば窓との位置関係を考える。

必要なら、

- 窓外の白飛び
- 室内奥の暗さ
- モニター光
- 廊下の照明
- 開いたドアからの光

を残す。

画面全体を均一に明るくしない。

---

## 4.13 FRAME

世界のすべてを一枚に表示しない。

最優先する被写体・行動を決め、それ以外は背景へ退かせる。

---

## 4.14 AFTER

写真のあと人物が何をするかを決める。

一枚のためだけに存在する場面にしない。

---

# 5. Reference Input 標準仕様

人物・背景・風景・衣装・小物・構図などを固定する入力ソースがある場合、必ずReference Inputとして扱う。

## 5.1 Reference Slot

標準スロットは以下とする。

### Reference A — Subject

人物参照。

固定候補:

- 顔
- 髪
- 年齢感
- 体格
- 肌色
- 耳/尻尾等の特徴
- 恒常アクセサリ

---

### Reference B — Environment

背景・部屋・空間参照。

固定候補:

- 部屋構造
- 家具配置
- 窓位置
- 出入口
- 壁/床
- 光源位置
- 主要設備

---

### Reference C — Wardrobe / Props

衣装・所有物参照。

固定候補:

- 衣装デザイン
- 柄
- 色
- アクセサリ
- 武器
- 扇子
- バッグ
- コントローラー
- 食器

---

### Reference D — Composition / Camera

構図・カメラ参照。

固定候補:

- Camera side
- camera height
- subject orientation
- foreground/background relation
- focal length family
- framing

---

### Reference E — Continuity

前カットEnd / 前Scene / 直前画像などの連続性参照。

特に動画生成では重要。

---

### Reference F — Additional

補助参照。

用途が明確な場合のみ使う。

---

# 6. Referenceの使用ルール

## 6.1 参照画像は「全部コピーする指示」ではない

参照画像には必ず**役割**を設定する。

例:

- 顔だけ参照
- 部屋構造だけ参照
- 衣装だけ参照
- 構図だけ参照
- 前カットとの差分維持に使用

---

## 6.2 Reference Priority

複数参照が衝突する場合に備えて優先順位を明示する。

既定優先順位:

1. Continuity Lock
2. Subject Identity
3. Environment Structure
4. Wardrobe / Owned Objects
5. Composition
6. Additional Reference

Scene固有条件で上書き可能。

---

## 6.3 Strictness

各Referenceに以下の固定強度を持たせる。

- Soft
- Medium
- Strict

### Soft

雰囲気/大枠を参考。

### Medium

主要特徴を維持。

### Strict

一致すべき要素として扱う。

---

# 7. Lock / Variation 標準仕様

## 7.1 Identity Lock

人物固定。

例:

- face structure
- hairstyle
- hair length
- body build
- eye colors
- clothing identity
- recurring accessories

---

## 7.2 Environment Lock

空間固定。

例:

- room layout
- furniture positions
- window placement
- door placement
- workstation structure
- architectural relationships

---

## 7.3 Continuity Lock

Start / EndまたはScene間で固定するもの。

例:

- same subject
- same outfit
- same room
- same primary props
- same camera family
- same world assumptions

---

## 7.4 Allowed Variation

自然に変えてよいもの。

例:

- pose
- gaze
- hand position
- facial micro-expression
- object position after use
- hair disturbance
- clothing wrinkles
- residual tension
- light change caused by action

---

# 8. Start Frame 標準定義

Start Frameは「動画が始まる前の静止画」ではない。

**これから主要Actionが起きる直前の安定状態**とする。

必要条件:

- 人物の目的が分かる
- 次の動きに接続できる姿勢
- 手・視線・道具に予備動作がある
- 主要Actionはまだ完了していない
- End Frameへ自然に動ける

---

# 9. End Frame 標準定義

End Frameは「適当に別ポーズへ変えた画像」ではない。

**主要Actionが起き終わり、その結果が人物・物・空間に残った収束状態**とする。

必要条件:

- Action結果が分かる
- 身体状態に結果が残る
- 小物位置や状態が変化している
- 次の生活行動へ移れる
- Start Frameと同じ世界・人物である

---

# 10. Start-End 差分設計

Start→Endで積極的に変えてよいもの:

1. 姿勢
2. 視線
3. 手・腕・指
4. 小物位置
5. 飲み物/食べ物/道具の状態
6. 衣服のシワ
7. 髪の乱れ
8. 光源状態
9. 微表情

原則固定するもの:

- 人物同一性
- 空間基本構造
- 衣装同一性
- 固有小物
- カメラFamily
- 世界設定

---

# 11. Start Frame デフォルトテンプレート Ver.2

```text
[SHOT_ROLE] = START FRAME.

Create a single image for AI video generation that depicts [SUBJECT_IDENTITY] in [LOCATION_TYPE / SPACE_STRUCTURE], at the moment just before [PRIMARY_ACTION]. Build the scene from the subject’s habits, movement, possessions, immediate purpose, and the physical consequences of the time leading into this moment.

REFERENCE INPUTS:
- Subject reference: [REFERENCE_IMAGE_A_ROLE]
- Environment reference: [REFERENCE_IMAGE_B_ROLE]
- Wardrobe / owned-object reference: [REFERENCE_IMAGE_C_ROLE]
- Composition / camera reference: [REFERENCE_IMAGE_D_ROLE]
- Continuity / previous-frame reference: [REFERENCE_IMAGE_E_ROLE]
- Additional reference: [REFERENCE_IMAGE_F_ROLE]

Reference usage policy: [REFERENCE_USAGE_POLICY].
Reference priority order: [REFERENCE_PRIORITY_ORDER].
Keep the subject consistent in: [IDENTITY_LOCK_SCOPE].
Keep the environment consistent in: [ENVIRONMENT_LOCK_SCOPE].
Maintain continuity in: [CONTINUITY_LOCK_SCOPE].
Allow natural variation only in: [ALLOWED_VARIATION_SCOPE].

The subject is currently [NOW_ACTION], with a clear non-camera-related objective. A short time earlier, they were [BEFORE_ACTION], leaving these specific physical traces: [ACTION_TRACES]. Place those traces only where they would naturally appear according to body position, object position, movement direction, contact, use order, and gravity.

The subject wears [WARDROBE_DESCRIPTION], chosen as believable personal clothing for their age, body, lifestyle, taste, and budget sense. Their hair, skin, sleeves, hems, wrinkles, posture, hands, and residual tension reflect the time immediately before the shot: [SUBJECT_STATE_DETAILS].

Include only necessary belongings that clearly belong to this person and support the current action: [OWNED_OBJECTS]. Place them according to real use and daily movement paths: [OBJECT_PLACEMENT_LOGIC]. Do not add decorative props without a functional or ownership reason.

The surrounding space is [SPACE_DETAILS]. Show only the portion necessary for this moment. Let the rest continue off-screen through cropping, occlusion, shadow, blur, depth, or partial framing. Visible background information is limited to [VISIBLE_BACKGROUND_ELEMENTS].

Off-screen context influencing body direction, hearing, or eye line: [OFFSCREEN_CONTEXT].

Lighting comes from [LIGHT_SOURCES_AND_DIRECTION]. Preserve natural falloff, localized brightness, shadow, and exposure differences instead of lighting the entire image evenly.

The camera is operated by [PHOTOGRAPHER_IDENTITY], photographing this moment because [PHOTOGRAPHER_REASON]. Use [CAMERA_HEIGHT_AND_DISTANCE], [LENS_DESCRIPTION], [EXPOSURE_FEEL], and [FRAMING_DESCRIPTION]. Visual priority: [VISUAL_PRIORITY].

This is the start frame. Preserve a poised pre-transition state. The body, gaze, hands, and object relationships should clearly make [NEXT_EXPECTED_MOTION] physically plausible, but that motion has not yet resolved.

Output one cohesive natural-language image-generation prompt only.
```

---

# 12. End Frame デフォルトテンプレート Ver.2

```text
[SHOT_ROLE] = END FRAME.

Create a single image for AI video generation that depicts [SUBJECT_IDENTITY] in [LOCATION_TYPE / SPACE_STRUCTURE], immediately after [PRIMARY_ACTION] has already taken place. Build the scene from the subject’s habits, movement, possessions, immediate purpose, and the physical consequences left by the completed action.

REFERENCE INPUTS:
- Subject reference: [REFERENCE_IMAGE_A_ROLE]
- Environment reference: [REFERENCE_IMAGE_B_ROLE]
- Wardrobe / owned-object reference: [REFERENCE_IMAGE_C_ROLE]
- Composition / camera reference: [REFERENCE_IMAGE_D_ROLE]
- Continuity / previous-frame reference: [REFERENCE_IMAGE_E_ROLE]
- Additional reference: [REFERENCE_IMAGE_F_ROLE]

Reference usage policy: [REFERENCE_USAGE_POLICY].
Reference priority order: [REFERENCE_PRIORITY_ORDER].
Keep the subject consistent in: [IDENTITY_LOCK_SCOPE].
Keep the environment consistent in: [ENVIRONMENT_LOCK_SCOPE].
Maintain continuity in: [CONTINUITY_LOCK_SCOPE].
Allow natural variation only in: [ALLOWED_VARIATION_SCOPE].

The subject has just completed or passed through [COMPLETED_ACTION] and is now in the brief settling moment of [NOW_ACTION_AFTER]. Immediately before this, they were [BEFORE_ACTION_FOR_END], leaving these specific physical results: [ACTION_RESULT_TRACES]. Place those traces only where they would naturally appear according to body position, object position, movement direction, contact, use order, and gravity.

The subject wears [WARDROBE_DESCRIPTION], maintaining continuity with the start frame and references. Their hair, skin, sleeves, hems, wrinkles, posture, hands, relaxation, or residual tension show what just happened: [SUBJECT_STATE_DETAILS_AFTER].

Include only necessary belongings that clearly belong to this person and support the finished moment: [OWNED_OBJECTS_AFTER]. Their changed positions or states follow from actual use: [OBJECT_PLACEMENT_LOGIC_AFTER]. Do not add decorative props without a functional or ownership reason.

The surrounding space is [SPACE_DETAILS]. Show only the portion necessary for this moment. Let the rest continue off-screen through cropping, occlusion, shadow, blur, depth, or partial framing. Visible background information is limited to [VISIBLE_BACKGROUND_ELEMENTS].

Off-screen context influencing body direction, hearing, or eye line: [OFFSCREEN_CONTEXT_AFTER].

Lighting comes from [LIGHT_SOURCES_AND_DIRECTION]. If the action changed an opening, display, lamp, fire, door, curtain, screen, or other light-affecting element, reflect the result naturally.

The camera is operated by [PHOTOGRAPHER_IDENTITY], photographing this moment because [PHOTOGRAPHER_REASON]. Use [CAMERA_HEIGHT_AND_DISTANCE], [LENS_DESCRIPTION], [EXPOSURE_FEEL], and [FRAMING_DESCRIPTION]. Visual priority: [VISUAL_PRIORITY].

This is the end frame. Preserve a settled post-transition state. The body, gaze, hands, object states, and spatial relationships should clearly show that [JUST_COMPLETED_RESULT] has already happened while remaining physically ready for [NEXT_AFTER_ACTION].

Output one cohesive natural-language image-generation prompt only.
```

---

# 13. 置換文字一覧

## Identity / World

- `[SUBJECT_IDENTITY]`
- `[LOCATION_TYPE / SPACE_STRUCTURE]`
- `[WARDROBE_DESCRIPTION]`
- `[SPACE_DETAILS]`

## Action Flow

- `[PRIMARY_ACTION]`
- `[BEFORE_ACTION]`
- `[NOW_ACTION]`
- `[ACTION_TRACES]`
- `[NEXT_EXPECTED_MOTION]`
- `[COMPLETED_ACTION]`
- `[BEFORE_ACTION_FOR_END]`
- `[NOW_ACTION_AFTER]`
- `[ACTION_RESULT_TRACES]`
- `[JUST_COMPLETED_RESULT]`
- `[NEXT_AFTER_ACTION]`

## Subject State

- `[SUBJECT_STATE_DETAILS]`
- `[SUBJECT_STATE_DETAILS_AFTER]`

## Objects

- `[OWNED_OBJECTS]`
- `[OWNED_OBJECTS_AFTER]`
- `[OBJECT_PLACEMENT_LOGIC]`
- `[OBJECT_PLACEMENT_LOGIC_AFTER]`

## Camera / Light / Frame

- `[VISIBLE_BACKGROUND_ELEMENTS]`
- `[OFFSCREEN_CONTEXT]`
- `[OFFSCREEN_CONTEXT_AFTER]`
- `[LIGHT_SOURCES_AND_DIRECTION]`
- `[PHOTOGRAPHER_IDENTITY]`
- `[PHOTOGRAPHER_REASON]`
- `[CAMERA_HEIGHT_AND_DISTANCE]`
- `[LENS_DESCRIPTION]`
- `[EXPOSURE_FEEL]`
- `[FRAMING_DESCRIPTION]`
- `[VISUAL_PRIORITY]`

## Reference

- `[REFERENCE_IMAGE_A_ROLE]`
- `[REFERENCE_IMAGE_B_ROLE]`
- `[REFERENCE_IMAGE_C_ROLE]`
- `[REFERENCE_IMAGE_D_ROLE]`
- `[REFERENCE_IMAGE_E_ROLE]`
- `[REFERENCE_IMAGE_F_ROLE]`
- `[REFERENCE_USAGE_POLICY]`
- `[REFERENCE_PRIORITY_ORDER]`
- `[IDENTITY_LOCK_SCOPE]`
- `[ENVIRONMENT_LOCK_SCOPE]`
- `[CONTINUITY_LOCK_SCOPE]`
- `[ALLOWED_VARIATION_SCOPE]`

---

# 14. Prompt Registry 標準登録案

BAI Video Production内では、将来的に次のテンプレートIDで管理する。

- `VISUAL_PROMPT_DIRECTOR_STARTFRAME_V2`
- `VISUAL_PROMPT_DIRECTOR_ENDFRAME_V2`

テンプレートはVersioned Assetとして扱い、過去Sceneの再現性を壊さない。

---

# 15. Scene Contract 追加項目

各Sceneは最低限以下を持てるようにする。

```json
{
  "subject_reference_set": [],
  "environment_reference_set": [],
  "wardrobe_reference_set": [],
  "composition_reference_set": [],
  "continuity_reference_set": [],
  "reference_priority_order": [],
  "identity_lock_scope": [],
  "environment_lock_scope": [],
  "continuity_lock_scope": [],
  "allowed_variation_scope": []
}
```

---

# 16. Validation / Gate

以下のGateを設計対象とする。

## 16.1 WORLD_INTEGRITY_GATE

生活設定と画面が矛盾していないか。

## 16.2 TRACE_PHYSICS_GATE

痕跡が行動・重力・接触と矛盾していないか。

## 16.3 OWNER_SPECIFICITY_GATE

カテゴリ名だけの所有物になっていないか。

## 16.4 FRAME_ECONOMY_GATE

画面が説明過多になっていないか。

## 16.5 REFERENCE_ROLE_COMPLETENESS_GATE

すべての参照に役割があるか。

## 16.6 IDENTITY_LOCK_GATE

人物固定条件を破っていないか。

## 16.7 ENVIRONMENT_LOCK_GATE

空間構造を破っていないか。

## 16.8 START_END_CONTINUITY_GATE

Start-Endの固定要素と可変要素が契約通りか。

## 16.9 VARIATION_SCOPE_GATE

許可されていない変化をしていないか。

---

# 17. BAI Video Production 表側UI設計

内部テンプレートを一般ユーザーへ直接見せない。

ユーザーには、

> 誰 / どこ / 何の途中 / 何を固定 / 何を変える

のUIとして提供する。

---

# 18. UI名称

推奨名称:

**Prompt Reference Workbench**

サブタイトル:

**Start / End Frame Director**

---

# 19. UIへの入口

## 19.1 Scene Inspector

Scene選択時、右Inspectorに以下を表示。

- Start Frame
- End Frame
- References
- Generate / Regenerate
- Open Prompt Workbench

---

## 19.2 Production Control

Plan → Scene → Asset Slotから、

- START_IMAGE
- END_IMAGE

を選び、`Generate Candidate`でWorkbenchを開く。

---

# 20. Workbench基本レイアウト

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ Prompt Reference Workbench                            Scene SC-xx        │
├──────────────────────┬───────────────────────────────┬───────────────────┤
│ INPUT                │ PREVIEW                       │ CONTRACT / AUDIT  │
│                      │                               │                   │
│ Scene                │ Start Frame                   │ Reference status  │
│ Subject              │ End Frame                     │ Identity Lock     │
│ Space                │                               │ Environment Lock  │
│ Action Flow          │ Start ⇄ End Difference       │ Continuity        │
│ References           │                               │ Validation        │
│ Locks & Variation    │ Continuity Strip              │ Advanced Prompt   │
│ Camera & Light       │                               │                   │
└──────────────────────┴───────────────────────────────┴───────────────────┘
```

---

# 21. UI — Sceneセクション

表示:

- Project
- Plan ID
- Scene ID
- Scene Name
- Slot Type
- Continuity Group

入力:

- Scene Theme
- Short Intent
- Target Use

---

# 22. UI — Subjectセクション

入力:

- Who is the subject?
- Age impression
- Gender impression
- Role / occupation
- Body build
- Face / hair notes
- Wardrobe
- Recurring personal objects

補助:

- `Import Character Contract`
- `Reuse Previous Scene Subject`

---

# 23. UI — Spaceセクション

入力:

- Location / Room Type
- Spatial Structure
- Key Furniture
- Visible Background
- Off-screen Context

補助:

- `Reuse Previous Environment`
- `Import Environment Contract`

---

# 24. UI — Action Flow

4段構成で表示する。

```text
BEFORE
  ↓
START NOW
  ↓
PRIMARY ACTION
  ↓
END / AFTER
```

入力:

- What was happening just before?
- What is happening at Start?
- What happens during the shot?
- What has changed at End?
- What happens next?
- Physical traces

---

# 25. UI — References

## 25.1 Reference Card

各ReferenceはカードUIにする。

表示項目:

- Thumbnail
- Asset Name
- Role
- Strictness
- Keep Notes
- Source Scene / Asset
- Remove / Replace

---

## 25.2 標準Referenceスロット

- Subject
- Environment
- Wardrobe / Props
- Composition
- Continuity / Previous Frame
- Additional

ユーザーはドラッグ&ドロップまたはAsset Browserから指定する。

---

# 26. UI — Lock & Variation

4領域を明示表示する。

## Identity Lock

Checkbox例:

- Face
- Hair
- Body build
- Eye color
- Outfit
- Accessories

## Environment Lock

Checkbox例:

- Room layout
- Furniture positions
- Window / door
- Workstation
- Architecture

## Continuity Lock

Checkbox例:

- Same subject
- Same outfit
- Same location
- Same primary props
- Same camera family

## Allowed Variation

Checkbox例:

- Pose
- Gaze
- Hands
- Object state
- Hair disturbance
- Clothing wrinkles
- Light state
- Facial micro-expression

---

# 27. UI — Reference Priority

ドラッグ並び替え形式で表示する。

例:

```text
1. Previous End Frame
2. Character Reference
3. Room Reference
4. Wardrobe Reference
5. Composition Reference
```

---

# 28. UI — Camera & Light

通常ユーザー向けには簡略入力。

- Camera side
- Camera height
- Distance
- Lens feel
- Framing
- Main light source
- Time of day

Advancedで詳細編集可能。

---

# 29. UI — Preview

中央にStart / Endを並べる。

```text
START FRAME            END FRAME
┌────────────┐         ┌────────────┐
│            │         │            │
│   image    │   →     │   image    │
│            │         │            │
└────────────┘         └────────────┘
```

---

# 30. UI — Difference View

StartとEndで変化した要素を一覧表示する。

例:

- Right hand: controller → desk
- Gaze: monitor → off-screen left
- Coffee: 70% → 50%
- Back posture: forward → relaxed

これは生成結果監査だけでなく、生成前の期待差分表示にも使う。

---

# 31. UI — Continuity Strip

```text
Prev End → Current Start → Current End → Next Start
```

を小型サムネイルで表示する。

Scene間の破綻をユーザーが一目で確認できるようにする。

---

# 32. UI — Validation Cards

右側に以下を表示。

- World Integrity
- Trace / Physics
- Owner Specificity
- Reference Completeness
- Identity Lock
- Environment Lock
- Continuity
- Frame Economy

状態:

- PASS
- WARNING
- FAIL

---

# 33. UI — Advanced Prompt

一般ユーザーには閉じておく。

Advancedを開いた場合のみ、

- Start Prompt
- End Prompt
- Template Version
- Filled Variables
- Reference Mapping

を確認可能にする。

ユーザーにPlaceholder名を常時見せない。

---

# 34. 通常ユーザーフロー

1. Sceneを選択
2. `Generate Start / End Frames`
3. Workbenchを開く
4. Subjectを確認
5. Spaceを確認
6. Action Flowを入力
7. Referenceを指定
8. Lock / Variationを確認
9. `Build Prompt Pair`
10. Validation
11. Preview生成
12. Candidate保存
13. Auditへ送る
14. Human Accept / Reject
15. LOCK

---

# 35. 前Sceneから継続する場合

前SceneのEnd Frameを自動でContinuity Referenceへ差し込む。

自動継承候補:

- Subject
- Environment
- Wardrobe
- Primary props
- Camera family

ユーザーは差分だけ入力する。

---

# 36. UIプリセット

## Lifestyle

- WORLD / TRACE / OWNERを重視
- Environment Lockは中

## Streamer / Creator Room

- Identity Lock強
- Environment Lock強
- Workstation Position強

## Start-End Motion Pair

- Continuity Lock最優先
- Allowed VariationをPose/Gaze/Hands/Object Stateに限定

## Character Continuity

- Identity Strict
- Costume Strict
- Environment Medium

---

# 37. UX原則

1. 内部Promptを表側へ露出しすぎない
2. Referenceには必ずRoleを設定させる
3. 何を固定し何が変わるかを生成前に表示する
4. Start / Endを別々に扱わずペアとして扱う
5. 前Sceneからの継続を簡単にする
6. Human Final Authorityを維持する
7. AI Candidate ≠ Approved Asset

---

# 38. 内部データモデル案

```json
{
  "scene_id": "SC-001",
  "slot_type": "PAIR",
  "template_version": "VISUAL_PROMPT_DIRECTOR_V2",
  "subject": {
    "identity": "...",
    "wardrobe": "...",
    "owned_objects": []
  },
  "space": {
    "location_type": "...",
    "structure": "...",
    "visible_background": "...",
    "offscreen_context": "...",
    "lighting": "...",
    "camera": "..."
  },
  "action_flow": {
    "before": "...",
    "start_now": "...",
    "primary_action": "...",
    "start_trace": "...",
    "end_now": "...",
    "end_trace": "...",
    "after": "..."
  },
  "references": [
    {
      "slot": "A",
      "role": "subject",
      "asset_id": "...",
      "strictness": "strict",
      "keep_notes": "..."
    }
  ],
  "locks": {
    "identity": [],
    "environment": [],
    "continuity": [],
    "allowed_variation": []
  },
  "reference_priority_order": []
}
```

---

# 39. BAI Development OS / Codexへの実装指示

実装時は以下を守る。

- 既存のPrompt Registry / Scene Contract / Production Controlの正本を先に読む
- 新規機能を重複実装しない
- Start / End Frame生成をVersioned Templateとして管理する
- Reference AssetはAsset Registryと統合する
- Candidate生成結果はAudit / Human Decision / LOCKへ接続する
- 既存Visual Compliance / Continuity / Prompt Registryが存在する場合は再利用する
- 新しいUIはTASK-036のUnified Desktop Applicationの見た目・操作原則を壊さない
- localhost/JSON/CLIを一般ユーザーの必須操作にしない
- Native file picker / Asset Browserを使う
- Human Final Authorityを維持する
- テンプレート更新によって既存Sceneの再現性を壊さない

---

# 40. 完了条件

本機能が完成したと言える最低条件:

- Start Frame V2 Templateが登録済み
- End Frame V2 Templateが登録済み
- Reference入力を構造化できる
- Identity / Environment / Continuity Lockを保持できる
- Allowed Variationを保持できる
- Start / End Pairを同一Scene Contractで扱える
- UIから参照画像を設定できる
- UIからLock/Variationを設定できる
- Prompt Pairを内部生成できる
- Candidate→Audit→Human Decisionへ接続できる
- 既存のVisual Compliance / Continuity Gateと連携できる
- Regression PASS
- Windows Native UIで実操作確認済み

---

# 41. 最終方針

このVisual Prompt Director Ver.2を、人物や生活空間を含むAI動画生成の**開始画像・終了画像の標準生成方式**として採用する。

固定するのは単なるPrompt文章ではなく、

- WORLD
- BEFORE
- NOW
- TRACE
- PHYSICS
- PLACE
- OWNER
- SUBJECT
- SPACE
- OFF-SCREEN
- CAMERA
- LIGHT
- FRAME
- AFTER
- REFERENCE
- LOCK
- VARIATION
- START-END CONTINUITY

からなる生成契約である。

BAI Video Productionの表側UIでは、その複雑さを一般ユーザーへ直接見せず、

> 誰 / どこ / 何をする / 何を参照する / 何を固定する / 何を変えてよいか

という操作へ翻訳する。

これを今後のStart / End Frame生成の標準設計とする。
