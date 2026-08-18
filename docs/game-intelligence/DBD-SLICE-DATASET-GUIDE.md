# DbD Slice Dataset Guide

## GUI / EXE first

For ordinary use, prefer [BAI DbD Training Studio](../user/DBD-TRAINING-STUDIO-USAGE.md). It can register one still image, import CSV with one row or many rows, or take a gameplay video and automatically extract/register exact-frame ROI slices for Survivor HUD, Perk slots and a calibrated Killer/Power ROI.

The CLI procedures below remain the reproducible low-level route and are useful for automation, troubleshooting and custom dataset workflows.

This guide describes how to cut, label, train, and evaluate HUD/icon slice images used by TASK-049.

## What is a slice?

A slice is a small ROI image cropped from an exact source frame. Examples:

- one survivor status slot from the lower-left HUD;
- one Item slot and two Add-on slots from the lower-left loadout HUD;
- one perk slot from the bottom-right HUD;
- upper-right notification text area;
- Killer / Power icon area.

Keep the source frame number and source video identity. Do not save only an anonymous PNG.

## Recommended directory

```text
datasets/dbd-recognition/
  source-manifests/
  survivor-hud/
    HEALTHY/
    INJURED/
    DOWNED/
    HOOKED/
    UNKNOWN/
  perks/
    perk_xxx/
    perk_yyy/
    UNKNOWN/
  killer/
  power/
  upper-right-ocr/
  hard-negatives/
  gold/
```

Do not commit copyrighted game captures to the public repository unless rights permit it. Local datasets can live outside Git and be referenced by manifest/hash.

## 1. Determine ROI

Use normalized coordinates:

```text
x, y, width, height = 0.0 .. 1.0
```

The source contains a broad discovery profile but it is **not an accuracy claim**. Calibrate ROI against the actual recording resolution/UI scale.

## 2. Extract exact-frame slices

Example:

```powershell
python .\tools\task049\extract-roi-slices.py `
  --video D:\dbd\match01-cfr.mp4 `
  --frames 1200,1201,1202,1203 `
  --roi-id bottom_right_perks `
  --x 0.72 --y 0.64 --width 0.28 --height 0.36 `
  --output-dir D:\dbd-dataset\raw-perks
```

This produces PGM grayscale slices with exact frame numbers in filenames and a `slice-manifest.csv` containing the source video path, exact frame, ROI ID and slice SHA-256. Keep that manifest beside the images so Human labels remain traceable.

The Training Studio performs the same conceptual flow from the GUI:

```text
video + Human label + exact frame range + slot/ROI
-> sampled exact frames
-> ROI slices
-> source provenance
-> visual-training.csv
-> reference index
```

For bulk supervised ranges, the GUI accepts `video-training-ranges-template.csv`. The file may contain **one row or many rows**.

Once a calibrated ROI profile exists, the easier form is:

```powershell
python .\tools\task049\extract-roi-slices.py `
  --video D:\dbd\match01-cfr.mp4 `
  --frames 1200,1201,1202,1203 `
  --roi-profile D:\dbd-dataset\roi-profile.json `
  --target perk:0 `
  --output-dir D:\dbd-dataset\perk-slot-0
```

Supported profile targets are `survivor:0..3`, `perk:0..3`, `upper-right`, `lower-left`, `bottom-right`, and `killer-power` when that optional ROI is defined. This avoids repeatedly copying coordinates by hand.

For Item/Add-on, extract `item_slot`, `addon_slot_0`, and `addon_slot_1` separately. Do not train the broad loadout ROI as one identity label.

For four perk slots, extract each calibrated sub-ROI separately. Do not assume all capture profiles use identical pixel geometry.


## 2.1 Extract each slot separately

For actual recognition, train **one visual contract per semantic slot/target**, not one large screenshot containing unrelated HUD. The runtime `DBDHudRoiProfile` has explicit four-slot ROI arrays. A calibrated profile may look like:

```json
{
  "schema_version": "1.1.0",
  "profile_id": "dbd-1080p-ui100-owner-v1",
  "lower_left_survivor_hud": {"roi_id":"lower_left_survivor_hud","x":0.0,"y":0.60,"width":0.30,"height":0.40},
  "upper_right_notifications": {"roi_id":"upper_right_notifications","x":0.55,"y":0.0,"width":0.45,"height":0.38},
  "bottom_right_perks": {"roi_id":"bottom_right_perks","x":0.72,"y":0.64,"width":0.28,"height":0.36},
  "survivor_slots": [
    {"roi_id":"survivor_slot_0","x":0.01,"y":0.625,"width":0.12,"height":0.08},
    {"roi_id":"survivor_slot_1","x":0.01,"y":0.715,"width":0.12,"height":0.08},
    {"roi_id":"survivor_slot_2","x":0.01,"y":0.805,"width":0.12,"height":0.08},
    {"roi_id":"survivor_slot_3","x":0.01,"y":0.895,"width":0.12,"height":0.08}
  ],
  "perk_slots": [
    {"roi_id":"perk_slot_0","x":0.82,"y":0.735,"width":0.075,"height":0.095},
    {"roi_id":"perk_slot_1","x":0.90,"y":0.735,"width":0.075,"height":0.095},
    {"roi_id":"perk_slot_2","x":0.82,"y":0.84,"width":0.075,"height":0.095},
    {"roi_id":"perk_slot_3","x":0.90,"y":0.84,"width":0.075,"height":0.095}
  ],
  "killer_power_hud": null
}
```

These coordinates are examples/discovery defaults, not a promise that every DbD capture uses those exact positions. Calibrate against real frames and version the profile.

For each slot, run `extract-roi-slices.py` with that slot's coordinates. Keep `slot` in the manifest/CSV group so per-slot accuracy can be measured.

## 3. Label

Use a CSV for reference training:

```csv
label,image_path,group
perk_windows_of_opportunity,D:\dbd-dataset\perk1.png,normal
perk_windows_of_opportunity,D:\dbd-dataset\perk1_active.png,active
perk_lithe,D:\dbd-dataset\perk2.png,normal
```

Survivor example:

```csv
label,image_path,group
HEALTHY,D:\dbd-dataset\hud_001.png,normal
INJURED,D:\dbd-dataset\hud_002.png,normal
DOWNED,D:\dbd-dataset\hud_003.png,normal
UNKNOWN,D:\dbd-dataset\transition_001.png,hard-negative
```

## 4. Build the deterministic baseline index

```powershell
python .\tools\task049\build-slice-reference-index.py `
  --csv D:\dbd-dataset\perk-reference.csv `
  --index-id dbd-perk-icons-v1 `
  --output D:\dbd-dataset\perk-index.json
```

The tool normalizes still images with FFmpeg and builds a checksum-protected reference index. The optional `group` column is preserved per sample, so the same canonical label can retain visual-state provenance such as `normal`, `active`, `greyed`, `transition`, or `hard-negative`.

The current baseline is **reference matching**, not a neural-network training run. This is useful because it is reproducible and establishes a benchmark quickly.

## 5. When to train a learned model

Move to a learned classifier only after collecting enough real examples and recording baseline failure modes.

A practical progression is:

```text
reference matching
-> hard-negative reference expansion
-> embedding nearest-neighbor
-> compact CNN/metric learning
-> calibrated ensemble if necessary
```

Keep `UNKNOWN` as a real class/decision. Never force every slice into a known perk/state.

## 6. Data augmentation

Use augmentation only on training data:

- resize/downscale/upscale;
- JPEG/video compression;
- mild blur;
- brightness/gamma variation;
- small crop/translation variation;
- HUD opacity variation when representative.

Avoid unrealistic transformations that change icon semantics.

## 7. Prevent leakage

Bad:

```text
frame 100 -> train
frame 101 -> test
```

Those frames are nearly identical.

Good:

```text
match A/B/C -> train
match D -> validation
match E/F -> test
```

## 8. Hard negatives

Store cases the recognizer got wrong:

```text
predicted perk_A, truth perk_B
predicted HEALTHY, truth transition/UNKNOWN
OCR CHASE, truth unrelated score text
Killer candidate, truth UI decoration
```

Every Human correction can become a hard-negative candidate after rights/provenance checks.

## 9. Gold Dataset

Gold labels must record at minimum:

- source asset/hash;
- match ID;
- exact frame range;
- ROI profile/version;
- label;
- Human labeler/reviewer reference;
- detector/index version;
- game patch/environment.

The benchmark must not feed the expected label into the detector.

## 10. Training output versioning

Every rebuilt model/index should have:

```text
model/index ID
training dataset hash
validation dataset hash
code revision
ROI profile version
created_at
KPI summary
```

Do not overwrite a previous model/index in place. Keep revisions so old analyses remain reproducible.

## Related

- [Recognition Accuracy and Training](DBD-RECOGNITION-ACCURACY-AND-TRAINING.md)
- [DbD Commentary Trivia Knowledge](DBD-COMMENTARY-TRIVIA-KNOWLEDGE.md)

## Calibrated ROIからSliceを作る

動画学習時は、可能な限りTraining Studioで作成したVersioned HUD Profileを指定してください。手動で毎回違う位置をCropせず、同じProfile/Anchor補正責任の下でSliceを作ることでDataset内の位置ばらつきを抑えられます。

Profile作成方法: [HUD Calibration / ROI Profile Guide](DBD-HUD-CALIBRATION-GUIDE.md)
