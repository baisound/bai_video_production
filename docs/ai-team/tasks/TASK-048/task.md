# TASK-048 — Voice Quality Calibration

- Status: `FORMALLY_ALLOCATED / DESIGN_QUEUED_AFTER_TASK_046_VERTICAL_SLICE`
- Authorization: `OWNER_DIRECTED_ROADMAP_AND_DESIGN`
- Governance: `DEV-4 FOUNDATION CRITICAL`
- Dependencies: `TASK-046`, `TASK-014`, `TASK-038`, `TASK-041`

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
