# DbD Recognition Accuracy and Training Guide

This guide explains how TASK-049 improves recognition accuracy for recorded Dead by Daylight video. It covers the current deterministic baseline and the upgrade path to learned models without changing CGEL contracts.

## Recommended GUI / EXE route

Normal teacher-data intake does not require manual CLI/CSV editing. Build and run **BAI DbD Training Studio**:

- [Build Training Studio EXE](../windows/BUILDING-DBD-TRAINING-STUDIO-EXE.md)
- [Training Studio Usage](../user/DBD-TRAINING-STUDIO-USAGE.md)

The GUI supports one sample, CSV with one or many rows, and direct video learning. Direct video learning samples exact frame numbers, extracts the calibrated ROI, records video/frame/ROI provenance and registers the resulting slices before index building.

CLI examples below remain useful for automation and diagnosis.

## Recognition targets

| Target | Current baseline | Main error sources | Accuracy improvement path |
|---|---|---|---|
| Lower-left survivor HUD | labeled ROI slice matching + temporal transition | UI scale, compression, status animation, overlays | ROI calibration → more labeled states → temporal voting → hard negatives → CNN/embedding model if needed |
| Upper-right text | OCR engine + DbD vocabulary resolver | motion blur, glow, language, short display time | frame burst OCR → preprocessing → vocabulary/alias expansion → confidence calibration → OCR fine-tuning only if necessary |
| Lower-left Item / Add-on loadout | per-slot reference slice matching + parent-anchor correction | icon state, charges/overlay, compression, Item/Add-on confusion | calibrate Item + two Add-on slots separately → collect normal/active/obscured/hard-negative slices → held-out Human Gold → UNKNOWN threshold calibration |
| Bottom-right four perk icons | per-slot reference slice matching + temporal voting | greyed/active states, low resolution, overlays, UI scale | collect every visual state → match per slot → hard-negative pairs → icon embedding/CNN → UNKNOWN calibration |
| Killer / Power | reference-image matcher + revisioned knowledge store | perspective-specific HUD, skins/UI revisions, similar iconography | separate Killer and Power datasets → patch-aware labels → hard negatives → temporal/multimodal fusion |
| Game event | Cross-modal Fusion into CGEL | one signal is ambiguous | combine Vision + HUD + OCR + ASR + State; require independent evidence for high-confidence claims |
| LLM commentary | existing BVP provider execution + deterministic Fact Validator | hallucinated numbers/effects/activation | feed only admitted facts/trivia; strict JSON claims; reject unsupported claims; keep provider execution explicitly authorized |


## Run the current recorded-video recognition baseline

After building labeled reference indexes, the current exact-frame baseline can be run directly against a normalized/CFR DbD recording. It executes the configured lower-left Survivor HUD detector, upper-right OCR, four bottom-right Perk slots, and optional Killer/Power ROI in one bounded pipeline.

```powershell
python .\tools\task049\run-recorded-video-recognition.py `
  --video D:\dbd\match01-cfr.mp4 `
  --frames 1200,1203 `
  --survivor-index D:\dbd-dataset\survivor-index.json `
  --perk-index D:\dbd-dataset\perk-index.json `
  --roi-profile D:\dbd-dataset\roi-profile.json `
  --output D:\dbd-evidence\recognition-1200-1203.json
```

If a calibrated Killer/Power ROI and index exist, also pass:

```text
--killer-power-index D:\dbd-dataset\killer-power-index.json
```

Upper-right OCR uses the optional `tesseract` CLI by default. Use `--no-ocr` when Tesseract is not installed. The command reports `production_accuracy_claim_authorized=false`; it is an evaluation/runtime baseline, not an automatic Production-accuracy declaration.

The default `DBDHudRoiProfile` contains **discovery coordinates only**. Record a calibrated JSON profile for the actual resolution/UI scale before benchmarking. The profile contains four explicit `survivor_slots`, four explicit `perk_slots`, the upper-right notification ROI, optional `item_slot` + two `addon_slots`, and an optional Killer/Power ROI.

## Accuracy rule

No recognition component is "production accurate" because synthetic fixtures pass. Production accuracy requires a **real-media Human Gold Dataset** and measured KPI evidence.

Measure at minimum:

- Precision / Recall / F1
- False Positive / False Negative
- UNKNOWN detection rate
- Abstention correctness
- calibration error
- temporal start/end error
- per-slot accuracy for the four perk slots
- per-state accuracy for survivor HUD
- OCR exact/normalized vocabulary match rate
- patch-compatible Killer / Power / Perk resolution rate

## Data split rule

Never randomly split adjacent frames from the same match across train and test. That leaks nearly identical images.

Use a split such as:

```text
Match A/B/C -> training
Match D     -> validation
Match E/F   -> test / Human Gold
```

If one source video contains several matches, split by `match_id`, not by individual frame.

## Lower-left survivor HUD

Recommended label set:

```text
HEALTHY
INJURED
DOWNED
HOOKED
DEAD
ESCAPED
UNKNOWN
```

For each state collect examples across:

- 720p / 1080p / 1440p / 4K source
- different UI scale
- streaming compression
- dark / bright maps
- transition animation frames
- status overlays
- spectator/recorded-video variations
- partially obscured HUD

Do not train only clean static screenshots. Add **hard negatives** such as transition frames that humans also find ambiguous.

Use temporal voting: one isolated frame should not normally override several neighboring frames unless the state transition itself is the evidence being detected.

## Upper-right text / notification OCR

The implementation uses an OCR port and a Tesseract CLI adapter. OCR output then goes through a bounded DbD vocabulary resolver.

Improve accuracy in this order:

1. calibrate the upper-right ROI for the actual capture profile;
2. sample several frames while the text is visible;
3. run OCR on each frame;
4. normalize Unicode and spacing;
5. vote across OCR results;
6. expand known Japanese/English aliases only from reviewed examples;
7. retain UNKNOWN for ambiguous text;
8. only then consider OCR model fine-tuning.

A single OCR string must not become a confirmed CGEL event by itself. Fuse it with another modality where possible.

## Bottom-right four perk icons

Treat each of the four slots independently.

Build a dataset that includes for each perk:

```text
normal icon
active/highlighted icon
greyed/disabled icon
partially occluded icon
compressed icon
small UI scale
large UI scale
```

A reference index can be built immediately from labeled slice images. The current baseline uses a deterministic 64-bit grayscale perceptual fingerprint. It is intentionally simple and gives a reproducible PoC baseline.

When reference matching reaches its limit, replace only the recognizer implementation with:

- compact CNN classifier;
- metric-learning model;
- image embedding nearest-neighbor index;
- ensemble of template + embedding scores.

Before moving to a learned model, export confusion pairs from Human corrections and preserve the `group` field (`normal` / `active` / `greyed` / `hard-negative`). Train on match-separated data, validate on a separate match set, and keep the final Human Gold matches completely held out. A learned model is accepted only when it improves the held-out KPI without degrading UNKNOWN/abstention behavior.

Keep the output contract the same:

```text
perk_id candidate
Top-K
confidence
UNKNOWN
```

Use confusion pairs as hard negatives. If two perk icons are repeatedly confused, add more examples for those two rather than only increasing total dataset size.

## Killer and Power

Killer and Power knowledge is stored separately from visual recognition. A detector should return an entity candidate, while the knowledge store resolves the patch-compatible VERIFIED revision.

Recommended datasets:

```text
killer_identity/
power_icon/
power_state/
unknown/
hard_negatives/
```

Do not assume a Killer because a Power icon resembles one historical version. Resolve visual candidate + game version + knowledge provenance.

## Cross-modal fusion

Preferred evidence strength:

```text
Visual/HUD/State > OCR > ASR > Knowledge-only inference
```

Knowledge is context, not proof that an event occurred.

High-confidence automatic confirmation should normally require more than one independent modality, for example:

```text
left HUD HEALTHY -> INJURED
+
attack visual evidence
+
ASR "一発もらった"
=
INJURY candidate with strong cross-modal evidence
```

## LLM commentary accuracy

The LLM is the final language layer, not the game-state detector.

Pipeline:

```text
CGEL CONFIRMED Event
+ patch-compatible facts
+ VERIFIED trivia
-> Commentary Plan
-> configured BVP LLM provider
-> strict JSON draft/claims
-> deterministic Fact Validator
-> Human/production flow
```

Provider execution requires explicit authorization. Unsupported numbers, perk effects, activations, Killer/Power claims, or trivia are rejected rather than silently accepted.

## Iterative accuracy loop

```text
Real video
-> ROI slices / OCR / detector output
-> Human Gold
-> KPI
-> confusion analysis
-> Hard Negative Dataset
-> retrain/rebuild reference index
-> regression
-> new real-media benchmark
```

Never tune directly against the final test set. Preserve a held-out match set for regression.

## Related guides

- [DbD Slice Dataset Guide](DBD-SLICE-DATASET-GUIDE.md)
- [DbD Commentary Trivia Knowledge](DBD-COMMENTARY-TRIVIA-KNOWLEDGE.md)
- [Windows EXE Usage](../user/WINDOWS-EXE-USAGE.md)

## HUD geometry calibration first

認識Datasetを増やす前に、対象録画のHUD Profileが正しくCalibrationされていることを確認してください。ROIずれを教師画像の追加だけで補おうとすると、不要なbackground差まで学習しFalse Positiveが増えます。

推奨順:

```text
HUD Calibration
-> Auto Profile Resolve確認
-> Anchor補正確認
-> Slice Dataset追加
-> Hard Negative追加
-> Human Gold再評価
```

操作は [HUD Calibration / ROI Profile Guide](DBD-HUD-CALIBRATION-GUIDE.md) を参照してください。
