# TASK-052 R5A — Bottom-right Status Icon Segmentation

Status: `IMPLEMENTED / VERIFIED`
Profile: `DEV-3 HIGH ASSURANCE`
Depends on: `R3C`, `R4B`, `R4C2`

## Goal

Split the calibrated bottom-right positive and negative status-effect regions into
zero, one or multiple body-free icon candidates. R5A owns region geometry and
segmentation only. Identity, source kind, visibility/state and Teacher/Gold review
belong to R5B/R5C.

## HUD Profile contract

HUD Profile schema `2.3.0` adds two optional normalized regions:

- `bottom_right_positive_effects` — left of the perk HUD;
- `bottom_right_negative_effects` — above the perk HUD.

Profiles `1.1.0` through `2.2.0` remain readable and restore both regions as
unavailable. Training Studio exposes both optional regions through the existing
pixel calibration editor. Anchor translation follows the canonical
`bottom_right_perks` parent correction without inventing uncalibrated geometry.

## Segmentation contract

`StatusIconSegmenter` applies a bounded deterministic contrast/component baseline
to an already extracted grayscale region. A result is exactly one of:

- `SEGMENTED` with one or more contiguous candidate ordinals;
- `EMPTY` with no partial candidate;
- `REGION_UNAVAILABLE` when the relevant Profile ROI is not calibrated;
- `OVERFLOW` with no partial candidate when the configured icon limit is exceeded.

Each candidate records only polarity, canonical region/ordinal ROI, foreground
count, segmentation score and a SHA-256 digest of the crop dimensions/pixels. Raw
pixels are not persisted in the recognition result. Positive and negative region
namespaces cannot be interchanged.

Inputs are bounded to 2048 pixels per dimension / 4,194,304 pixels and at most 64
configured icon candidates. The default recorded-video extraction is 384x192.

## Recorded-video integration

When a segmenter is configured, `DbDRecordedVideoRecognizer` extracts each
calibrated status region once, records the region-level `SliceArtifact`, segments
it, and adds at most one result per polarity to `DBDFrameRecognition`. Missing
regions produce explicit unavailable results rather than fake negative Evidence.
No temporal state or CGEL/Production mutation occurs in R5A.

## Acceptance

- zero, one and multiple synthetic icon regions produce deterministic results;
- component overflow exposes no partial candidates;
- polarity/region cross-namespace input fails closed;
- candidate outputs contain body-free crop digest and no pixel body;
- Profile 2.3 round-trips and prior schemas remain readable;
- recorded-video routing extracts both regions and reports missing calibration;
- Training Studio exposes both optional calibration regions;
- existing DbD vision, calibration, recognition and Training Studio regressions
  remain green.

## Verification

- focused R5A/Profile/recorded-video/calibration regression: `29 PASS`;
- TASK-049 DbD + TASK-050/051/052 affected regression: `370 PASS`;
- compileall: `PASS`;
- unresolved Critical/High findings: `0 / 0`.
