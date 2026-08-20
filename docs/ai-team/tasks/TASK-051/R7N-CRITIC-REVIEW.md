# TASK-051 R7N — Critic Review

## Decision

`APPROVE_WITH_WINDOWS_HUMAN_ACCEPTANCE_REQUIRED`

## Accepted decisions

1. Keep Training Studio as authoring/calibration and add a separate use-path for video analysis/export.
2. Do not let external CANDIDATE data silently become teacher truth.
3. Preserve the last Human-verified external revision while a changed web snapshot waits for review.
4. Remove raw-ID correction from normal visual review and use image/name search.
5. Treat add-ons as owner-related entities, not unscoped names.
6. Treat Map Image Training as a localization dataset problem: canonical orientation, floor, normalized UV, landmark/region and cross-view role are first-class.
7. Export editing information without directly mutating Human-owned NLE/production timelines.
8. Keep weak OCR/ASR as findings rather than fabricating Canonical Game Event Timeline events.

## Residual risks / non-claims

- Kamigame HTML can change; the parser is evidence-first and must surface collection failures rather than silently invent data.
- Cached external images are review convenience and may be unavailable if the external host changes or blocks downloads.
- Pillow is added to the Windows build contract; packaged Human Acceptance must confirm JPEG/WebP image display and rotation.
- Map localization runtime/model is not implemented; R7N provides dataset/contracts only.
- Direct DaVinci/Premiere project mutation is not implemented by this unit. The output is a safe handoff/marker package for downstream adapters.
- Full-match canonical event generation remains bounded by the existing DbD Game Intelligence recognition stack and Human Gold calibration; ASR/OCR alone is not treated as canonical match truth.
