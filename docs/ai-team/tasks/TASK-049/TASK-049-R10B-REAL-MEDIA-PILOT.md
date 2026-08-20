# TASK-049 R10B — Real-media / Human-Gold Pilot

- Date: `2026-08-18`
- Current state: `R10B0-R10B5 BOUNDED RECOGNITION/KNOWLEDGE/LLM/TRIVIA BASELINES IMPLEMENTED / R10B6 REAL-MEDIA CALIBRATION + HUMAN GOLD KPI PENDING`
- Development depth: `DEV-3 HIGH ASSURANCE` for accuracy/evaluation semantics
- Production accuracy claim: `NOT AUTHORIZED`

## Objective

Measure a concrete DbD detector on real media without leaking Human Gold labels into the detector and without confusing a bounded benchmark with production-quality recognition.

R10B is now split into:

```text
R10B0  Native-media pilot infrastructure
R10B1  ROI/slice + recorded-video recognizer baseline
R10B2  Survivor HUD / OCR / Perk / Killer-Power recognition baseline
R10B3  Cross-modal Fusion
R10B4  LLM commentary provider integration
R10B5  Trivia Knowledge / manual maintenance utility
R10B6  Real-media calibration + Human Gold measurement / threshold proposal
```

## R10B0 implemented contract

### Human Gold

`EventBenchmarkCase` now distinguishes:

```text
evaluation_range
    = bounded real-media window shown to the detector

expected_event_type / expected_range
    = Human Gold answer used only by the evaluator
```

For R10B, `evaluation_range` is mandatory even for a positive case. The detector does not receive the expected event type/range, labeler reference, or case identifier.

Persisted benchmark datasets have deterministic `dataset_sha256` integrity validation and a public/package JSON Schema mirror:

```text
schemas/game-event-benchmark-dataset.schema.json
src/ai_video_production/schema_resources/game-event-benchmark-dataset.schema.json
```

### Exact bounded frame sampling

`FFmpegPNGFrameSource` reads exact decoded frame indices through FFmpeg using a bounded sampling policy.

Properties:

- no shell execution;
- exact requested frame index provenance;
- PNG hash captured per sampled frame;
- timeout and maximum decoded PNG size;
- no canonical host path written into the pilot report;
- no full-match high-throughput claim.

### Detector port

`NativeDBDVisualDetector` receives only:

```text
sampled PNG frames
evaluation frame range
exact source FrameRate
```

It does not receive:

```text
expected event class
expected event range
Human labeler
benchmark case ID
```

The concrete deterministic recorded-video recognition baseline is implemented separately. It remains uncalibrated until real DbD media/reference data is admitted.

### Evidence -> CGEL

A detector assertion is converted through existing TASK-049 contracts:

```text
NativeVisualDetection
  -> GameEvidence(VISION)
  -> BoundedDBDEventProducer
  -> DBDEventResolver
  -> Canonical Game Event
  -> optional append-only GameIntelligenceStore
  -> R10A benchmark evaluator
```

Low-confidence output still follows R4 UNKNOWN/NEEDS_REVIEW policy.

### Accuracy authority

A native pilot report records:

```text
native_media_evidence = true
production_accuracy_claim_authorized = false
```

Synthetic/non-native evidence cannot mint production-accuracy authority. Human-Gold + native-media evidence is necessary but still not sufficient; a separate explicit policy/Owner decision is required for any production threshold.


## Human Gold authoring helper

For R10B1, Human labels can be authored in a small CSV and compiled to the canonical hashed JSON contract:

```text
case_id,evaluation_start_frame,evaluation_end_frame_exclusive,expected_event_type,expected_start_frame,expected_end_frame_exclusive,expected_abstention
```

Compiler:

```powershell
python .\tools\task049\compile-r10b-human-gold.py `
  --csv .\evidence\task049-r10b\gold.csv `
  --source-asset-id ASSET-... `
  --dataset-id dbd-r10b-pilot `
  --revision 1 `
  --labeler-ref human://owner-review-1 `
  --output .\evidence\task049-r10b\gold.json
```

The compiler enforces exact frame ranges, explicit abstention semantics, source Asset identity, Human labeler provenance and dataset SHA-256. `UNKNOWN_EVENT` is not a Human Gold class; ambiguous/negative examples are represented as abstention cases.

## Current bounded recorded-video recognition surface

The implemented baseline can now produce/read:

```text
Lower-left four Survivor slots
  HEALTHY / INJURED / DOWNED / HOOKED / DEAD / ESCAPED / UNKNOWN

Upper-right OCR
  bounded notification vocabulary (e.g. WINDOW_VAULT / HOOK / UNHOOK; ambiguous text remains non-confirming)

Bottom-right four Perk slots
  Top-K reference candidates / perk_id or UNKNOWN

Optional Killer/Power ROI
  killer_* / power_* candidate or UNKNOWN
```

State transitions can create bounded INJURY / DOWN / HOOK / UNHOOK / KILL / ESCAPE observations. Cross-modal Fusion combines compatible modalities. This is an implemented baseline, not a Production-accuracy claim.

## Verification

Focused R10B0 + R10A + Human Gold authoring tests:

```text
18 PASS
```

Combined TASK-049 R1-R10B0 + TASK-009 focused regression:

```text
129 PASS
```

## Real-media decode preflight

Before implementing/tuning a concrete detector on a newly admitted video, verify that every Human Gold evaluation window can be decoded at exact requested frame indices:

```powershell
python .\tools\task049\run-r10b-media-preflight.py `
  --video <normalized-cfr-video> `
  --gold .\evidence\task049-r10b\gold.json `
  --frame-rate 30000/1001 `
  --output .\evidence\task049-r10b\media-preflight.json
```

The receipt contains sampled frame indices/hashes and intentionally excludes expected labels and Human labeler identity. It records `accuracy_measured=false`; a PASS here proves decode/timebase readiness only, not recognition quality.

## R10B6 prerequisites

To continue from the implemented baseline to actual accuracy development, provide/admit:

1. a real DbD source video under permitted rights;
2. its BVP admitted/normalized CFR analysis Asset;
3. a calibrated ROI profile for the actual UI scale/resolution;
4. reviewed Survivor/Perk/Killer/Power slice reference data;
5. Human Gold evaluation windows, including positive and abstention/negative windows.

Once real media is available, run decode/timebase preflight, execute the baseline, measure false positives/false negatives/UNKNOWN/calibration/timing, then improve data/thresholds from the measured confusion set. Introduce a learned model only if the held-out KPI shows reference matching is insufficient.

## Explicit non-goals

R10B0 does not:

- claim any DbD detector accuracy;
- read game process memory;
- inject into the game;
- use anti-cheat hooks;
- call paid/cloud providers;
- modify Production Timeline;
- write Resolve;
- authorize publication/release.
