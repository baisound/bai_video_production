# DbD HUD Calibration / ROI Profile Guide

## 1. Purpose

`BAI DbD Training Studio.exe` の **HUD Calibration** タブは、録画ごとに画面のどこを認識するかを推測させるのではなく、Humanが一度確認したHUD位置を **Versioned HUD Profile** として保存するための機能です。

対象:

- 左下 Survivor HUD 全体
- 左下 Survivor Slot 1〜4
- 右上 Notification / Text領域
- 右下 Perk HUD 全体
- 右下 Perk Slot 1〜4
- Killer / Power HUD（必要なProfileのみ）

Profileが解決できない場合、実認識は座標を推測して続行せず fail-closed します。

## 2. Canonical rule

保存する座標は1920x1080等の固定pixel座標ではなく、画面幅・高さに対する正規化座標です。

```text
x / frame_width
y / frame_height
width / frame_width
height / frame_height
```

これにより、同じHUD配置を持つ同系統の解像度へ再利用できます。一方、UI Scaleやアスペクト比、DbDのHUD変更が異なるProfileを無理に共有しません。

## 3. GUIでProfileを作る

1. `BAI DbD Training Studio.exe` を起動します。
2. **HUD Calibration** タブを開きます。
3. `Video / still image` でDbD録画または静止画を選択します。
4. 動画の場合はHUDが明瞭な `Frame index` を入力します。
5. `Load preview` を押します。
6. `ROI target` を選びます。
7. Preview上で対象領域をマウスドラッグします。
8. 必要なROIを順番に登録します。
9. `Profile ID / Version / UI Scale / Game version` を入力します。
10. `Save versioned profile + anchors` を押します。

最低限、通常のSurvivor視点解析では次を登録します。

```text
lower_left_survivor_hud
survivor_slot_0..3
upper_right_notifications
bottom_right_perks
perk_slot_0..3
```

左下のLoadoutも解析するProfileでは、Survivor状態領域とは別に次を登録します。

```text
lower_left_loadout_hud
item_slot
addon_slot_0
addon_slot_1
```

`lower_left_loadout_hud` はItem 1枠 + Add-on 2枠の親Anchor領域です。Item/Add-onの子ROIをSurvivor状態ROIや親ROIと混ぜず、個別にドラッグ登録してください。

Killer / Power表示を使うProfileでは `killer_power_hud` も登録します。

## 4. Anchor clip

Profile保存時、主要ROIから参照クリップを自動保存します。

```text
Training workspace/
  hud_profiles/
    <profile_id>/
      profile.json
      anchors/
        lower_left_survivor_hud.pgm
        lower_left_loadout_hud.pgm      # configured only
        upper_right_notifications.pgm
        bottom_right_perks.pgm
        killer_power_hud.pgm   # configured only
```

Profile JSONにはAnchor画像そのものではなく、次を保持します。

- ROI ID
- dHash feature
- SHA-256
- source reference

これにより、Profile選択と微小位置補正時に参照できます。

## 5. Auto Profile Resolve

Runtimeでは、登録Profileを次の情報で絞ります。

1. Frame resolution
2. Aspect ratio
3. UI Scale（指定時）
4. DbD game version range
5. Anchor similarity（Anchorがある場合）

最上位Profileが十分なscoreを持たない、または複数Profileが僅差の場合は自動選択しません。

```text
UNKNOWN HUD PROFILE
or
AMBIGUOUS HUD PROFILE
```

としてCalibrationを要求します。

Training Studioの `Test auto profile + anchor correction` で実動画に対する解決結果を事前確認できます。

## 6. Anchor micro-alignment

固定ROIだけでは録画処理・capture scaling・数pixelのずれに弱いため、Runtimeでは登録Anchorの周辺だけを探索できます。

既定baseline:

```text
search radius: +/- 8 px
step: 4 px
```

Anchor補正は **平行移動だけ** です。

- 勝手なscale変更をしない
- ROI sizeを変えない
- confidence不足なら補正しない
- parent HUD anchorのshiftを、その配下slotへ同じように適用する

例:

```text
bottom_right_perks  dx=-4 px, dy=+4 px
    -> perk_slot_0..3 へ同じshift

lower_left_loadout_hud dx=+4 px, dy=0 px
    -> item_slot / addon_slot_0..1 へ同じshift
```

## 7. Runtime recognition integration

`DbDRecordedVideoRecognizer` は任意で次を受け取れます。

```text
DBDHudVideoProfileResolver
HudAnchorAligner
```

処理順:

```text
DbD video
  -> frame geometry
  -> calibrated Profile resolve
  -> bounded Anchor alignment
  -> corrected ROI
  -> Survivor / Item-Addon / OCR / Perk / Killer-Power detector
  -> Cross-modal Fusion
  -> CGEL
```

Profile resolverを有効にしている場合、Profile不明をDiscovery座標で誤魔化しません。

## 8. Profileを新しく作るべき時

次の場合は既存Profileを無理に流用せず、新しいProfile VersionまたはProfile IDを作成してください。

- 16:9 -> 21:9等のAspect変更
- DbD UI Scale変更
- DbDアップデートでHUD位置/形状が変化
- 配信Overlay等で基準HUDが移動/切り取られる
- capture softwareによるletterbox/crop
- Anchor scoreが継続して低い

同じ条件の微調整ならProfile Versionを上げ、条件自体が異なる場合は別Profile IDを推奨します。

## 9. Accuracy improvement

Calibrationは精度改善の最初の段階です。Profile作成後は [DbD Recognition Accuracy & Training](DBD-RECOGNITION-ACCURACY-AND-TRAINING.md) と [DbD Slice Dataset Guide](DBD-SLICE-DATASET-GUIDE.md) に従い、各ROIのnormal / active / greyed / compression / hard-negative / unknown Sliceを追加してください。

## 10. Migration

HUD ProfileとAnchor画像はTraining Studio workspace配下に保存されるため、DbD Data Migration BackupのTraining scopeに含まれます。別PCへ移行するときは [DbD Data Backup / Restore](../user/DBD-DATA-BACKUP-RESTORE.md) を使用してください。


## 左下 Item / Add-on Loadout

左下は `Survivor Status` と `Item / Add-on Loadout` を別系統としてCalibrationします。`lower_left_loadout_hud`, `item_slot`, `addon_slot_0`, `addon_slot_1` を登録し、親Anchor補正を子3枠へ伝播します。
