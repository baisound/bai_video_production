# TASK-048 — Voice Quality Calibration

- Status: `CANONICAL_FOUNDATION_HOSTED_CLOSED / LIVE_CALIBRATION_AND_AUTO_DECISION_GATED`
- Authorization: `HOSTED_CLOSED_FOUNDATION / FUTURE_EFFECTS_REQUIRE_FRESH_AUTHORITY`
- Governance: `DEV-4 FOUNDATION CRITICAL`
- Dependencies: `TASK-046`, `TASK-014`, `TASK-038`, `TASK-041`

## Hosted closure

- P-QC-1A canonical voice-quality calibration metadata contract passed all
  `9 / 9` hosted checks in PR #106 and merged at exact main
  `458b671fb2a00e0ec820edde4e6cefea6b766059`; its implementation and
  CHANGELOG locks closed through PR #108.
- P-QC-1B local GAIN receipt admission passed all `9 / 9` hosted checks in
  PR #136 and merged at exact main
  `82c9191791a76a1cc76784e01a12816899cebc9a`; its lock closed through
  PR #137.
- Both foundations are pure metadata contracts. Real audio reads, analyzer or
  hardware/OBS execution, canonical quality receipt issuance, Dataset/Asset
  promotion, Training/Model use and automatic Human decisions remain outside
  their authority.

## Goal

Calibrate version-pinned voice/audio analyzers against consented Human review
so quality indicators are explainable and reproducible instead of an
unqualified "95% quality" claim.

## Boundaries

- Training Dataset and Calibration Dataset are logically and physically
  separate.
- Raw and calibrated scores, Analyzer/Profile versions, scope, sample counts,
  reviewer agreement and decision trace are retained.
- Hard failures such as corrupt audio, silence, critical term loss, clipping
  and speech-end overflow override aggregate scores.
- Auto Approve and Auto Reject remain OFF until a separately authorized,
  sample-sufficient validated profile exists.
- Normal review is Owner-led; formal VoiceProfile/Release calibration adds a
  consented blind re-evaluation.
- Threshold changes never rewrite historical decisions silently.

## Exit criteria

Gold labels, grouped validation split, threshold simulation, false-positive/
false-negative reporting, drift detection and export decision trace pass
without exposing private audio or creating autonomous Human decisions.
