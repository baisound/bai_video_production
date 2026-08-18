# BAI DbD Training Studio Usage

`BAI DbD Training Studio.exe` is the normal GUI route for adding DbD recognition teacher data and commentary knowledge. CLI tools remain available for advanced automation, but manually editing CSV or running Python commands is not required for ordinary intake.

## Start the application

After building:

```powershell
& ".\builds\BAI DbD Training Studio\BAI DbD Training Studio.exe"
```

The default local workspace is under:

```text
%LOCALAPPDATA%\BAI Video Production\training\dbd
```

It contains manifests, extracted video slices, OCR candidates, transcript artifacts, indexes and the local trivia SQLite store.

## Input routes at a glance

| Learning / knowledge target | One item in GUI | CSV one row | CSV many rows | Direct video learning |
|---|---:|---:|---:|---:|
| Survivor HUD visual states | Yes | Yes | Yes | Yes |
| Perk icon visual states | Yes | Yes | Yes | Yes |
| Killer / Power visual identity | Yes | Yes | Yes | Yes, calibrated ROI required |
| Upper-right OCR vocabulary | Yes | Yes | Yes | Yes, OCR candidates require Human selection |
| Commentary Trivia | Yes | Yes | Yes | Yes, local ASR produces CANDIDATE entries |

A CSV import button accepts the same file whether it contains **one data row or many data rows**.

## 1. Visual Training: one image

Use **Visual Training** when a prepared slice image already exists.

1. Select `SURVIVOR_HUD`, `PERK_ICON`, or `KILLER_POWER`.
2. Enter the canonical label.
3. Browse the slice image.
4. Set the visual group, for example `normal`, `active`, `greyed`, `transition`, or `hard-negative`.
5. Press **Register 1 sample**.
6. Build/rebuild the reference index when the reviewed dataset is ready.

The reference index preserves visual group provenance.

## 2. Visual Training: CSV one or bulk

Press **Import CSV (1 or many rows)**.

Template:

```text
<workspace>\templates\visual-training-template.csv
```

Required columns are `label` and `image_path`; `domain` can be supplied per row or selected in the GUI.

## 3. Video Learning: supervised exact-frame slice extraction

Use **Video Learning** when the teacher examples are still inside a gameplay recording.

1. Browse the owned/permitted DbD recording.
2. Optionally choose a calibrated ROI profile JSON.
3. Choose the target domain.
4. For Survivor or Perk, choose slot `0..3`.
5. Enter the **correct Human label** for the selected range.
6. Enter:
   - start frame;
   - end frame exclusive;
   - frame step;
   - maximum samples.
7. Press **Extract + register from video**.

The application performs:

```text
video
-> exact frame numbers
-> calibrated ROI
-> PGM slice
-> provenance (video/frame/ROI)
-> visual-training.csv
-> later reference-index build
```

For example, `start=1000`, `end=1600`, `step=30` samples every 30 frames in that Human-reviewed range. Do not label a long range with one label unless the label is actually valid throughout the range.

### Killer / Power video learning

The discovery ROI intentionally does not guess the Killer/Power HUD location. Supply an ROI profile containing `killer_power_hud`; otherwise the Training Studio fails closed.

## 4. Video ranges by CSV

For many labeled ranges, use **Import video ranges CSV (1 or many rows)**.

Template:

```text
<workspace>\templates\video-training-ranges-template.csv
```

Important fields:

```text
domain
label
video_path
start_frame
end_frame_exclusive
frame_step
slot
group
roi_profile_path
max_samples
```

This is the preferred bulk route when Human review has already produced many exact-frame ranges.

## 5. Upper-right OCR learning from video

The Training Studio can scan the upper-right notification ROI directly from a recording.

1. Use the same video/frame-range fields in **Video Learning**.
2. Set Tesseract executable and OCR language if needed.
3. Press **Scan video OCR candidates**.
4. Review the displayed OCR strings.
5. Enter the correct `Signal ID`.
6. Select only valid phrases.
7. Press **Register selected phrases**.
8. In **Upper-right OCR**, build the vocabulary JSON.

Scanning alone **does not mutate the vocabulary**. This prevents bad OCR from teaching itself.

## 6. Commentary Trivia from video

Open **Commentary Trivia**.

You can:

- manually register one item;
- import CSV one/many;
- mine an existing BVP `TranscriptManifest` JSON;
- select a video and press **Transcribe video + mine candidates**.

Direct video mode uses local FasterWhisper. Model download is OFF by default. If the model is not already cached, either prepare it separately or explicitly allow model download.

All automatically mined statements are stored as:

```text
CANDIDATE
```

They do not become reusable commentary knowledge until Human verification.

## 7. Build indexes / vocabulary

After reviewed examples are registered:

- Visual Training -> **Build reference index**;
- Upper-right OCR -> **Build vocabulary JSON**.

Keep old index versions when benchmarking a new one. Do not overwrite the only copy of a known-good index.

## 8. Accuracy improvement loop

Use this loop for each visual target:

```text
real video
-> extract/labeled slices
-> train/reference index
-> held-out match evaluation
-> confusion / false-positive review
-> hard negatives
-> rebuild
-> re-evaluate
```

Do not train and evaluate on adjacent frames from the same match. See [Recognition Accuracy and Training](../game-intelligence/DBD-RECOGNITION-ACCURACY-AND-TRAINING.md).

## 9. Current limitation

The GUI currently builds the deterministic reference-slice recognition baseline. It does not yet run CNN/embedding fine-tuning. The manifests, source provenance, groups, exact-frame slices and Human Gold separation are deliberately structured so a learned visual backend can later consume the same reviewed data.


## 10. Backup / Restore for PC migration

Open **Backup / Restore** to create one portable checksum-verified ZIP for the DbD-specific data you want to move to another PC.

The GUI can include:

- the selected BVP Project's `.bvp/game-intelligence` databases;
- the complete Training Studio workspace (CSV, slices, indexes, OCR, transcripts and training trivia);
- the global Trivia Editor knowledge database.

Use **Preview restore** before every restore. Existing differing data is never replaced from preview alone. If Human replacement is confirmed, Training Studio creates a pre-restore safety backup automatically. Provider API keys and private-key/credential files are never part of this migration bundle.

See [DbD Data Backup / Restore and PC Migration](DBD-DATA-BACKUP-RESTORE.md) for the full old-PC -> new-PC procedure and integrity rules.

## Related

- [Build the Training Studio EXE](../windows/BUILDING-DBD-TRAINING-STUDIO-EXE.md)
- [Recognition Accuracy and Training](../game-intelligence/DBD-RECOGNITION-ACCURACY-AND-TRAINING.md)
- [Slice Dataset Guide](../game-intelligence/DBD-SLICE-DATASET-GUIDE.md)
- [Commentary Trivia Knowledge](../game-intelligence/DBD-COMMENTARY-TRIVIA-KNOWLEDGE.md)
- [DbD Data Backup / Restore and PC Migration](DBD-DATA-BACKUP-RESTORE.md)

## HUD Calibration / ROI Profile

Training Studioの **HUD Calibration** タブでは、動画または静止画を開き、左下Survivor HUD、右上通知、右下Perk、各4 slot、Killer/Power領域をPreview上でドラッグ登録できます。

保存時には正規化座標、元解像度、UI Scale、DbD Version、Profile Versionと主要HUDのAnchor clipを同時保存します。`Test auto profile + anchor correction` でProfile自動選択と微小補正を事前確認できます。

詳しい操作、Profileを作り直す条件、Fail-closedの意味は [HUD Calibration / ROI Profile Guide](../game-intelligence/DBD-HUD-CALIBRATION-GUIDE.md) を参照してください。


## Left-bottom Item / Add-on learning

The lower-left HUD is split into two independent systems: Survivor status and Item/Add-on loadout. In **HUD Calibration**, register `lower_left_loadout_hud`, `item_slot`, `addon_slot_0`, and `addon_slot_1`. In **Video Learning**, select `ITEM_ICON` with a blank slot for Item training, or `ADDON_ICON` with slot `0` or `1` for Add-on training. One image, one CSV row, many CSV rows, and direct-video exact-frame extraction all use the same visual-training manifest. Labels should use stable IDs such as `item_medkit` and `addon_bandages`; weak or ambiguous slices should be retained as hard negatives rather than forced into a label.

## Knowledge Import: Kamigame Candidate Collection

The **Knowledge Import** tab can collect the user-approved Kamigame Survivor Perk, Killer Perk and Killer-list pages. Killer detail traversal is optional. The result is a review bundle under the selected output directory; it does not modify canonical Perk/Killer Knowledge automatically.

See [DbD Kamigame Knowledge Candidate Import](../game-intelligence/DBD-KAMIGAME-KNOWLEDGE-IMPORT.md).
