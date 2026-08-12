# TASK-010 Source Linked A/V Preservation Detailed Design

- Date: 2026-08-13
- Status: IMPLEMENTATION CANDIDATE / NATIVE EVIDENCE AVAILABLE
- Parent: TASK-010 Resolve Assembly MVP
- Evidence basis: TASK-010 Native Validation Phase 2 `linked_av_status=PASS`

## 1. Finding

Phase 2 product cases produced two video keep items and zero source-audio items for all tested source rates. The isolated linked-A/V semantic probe, using the same generated A/V source with `mediaType` omitted, produced both video and audio in Resolve.

Therefore the existing primary-source `mediaType=1` behavior is insufficient for the minimum editing workflow.

## 2. Decision

The canonical primary-source placement mode becomes `LINKED_AV`.

Primary source placement omits `mediaType`. Supplementary `AudioPlacement` remains a separate audio-only Asset contract.

## 3. Identity safety

The linked-A/V behavior must not reuse deterministic identity created under video-only semantics.

- `assembly_plan_version`: `1.0.0 -> 1.1.0`
- add `source_media_mode=LINKED_AV`
- include source media mode in Timeline-name identity
- include source media mode in assembly SHA-256
- never silently reinterpret an old Automation Timeline as a linked-A/V result

## 4. Timebase contract

Source trim math is unchanged and uses the real source FPS:

- source start: floor
- source end-exclusive: ceil
- Resolve inclusive end: end-exclusive - 1
- Timeline record frame: TASK-022 mapping output

Timeline FPS may not replace source FPS.

## 5. Append semantics

Each keep range is appended independently and requires a non-empty Resolve response. This avoids assuming that linked A/V returns exactly one TimelineItem per source range.

If a later keep range fails after an earlier mutation, no final assembly marker is written. The existing partial-state gate then fails closed on retry.

## 6. Native acceptance

A fresh sandbox must prove:

1. 30/1 source -> 30/1 Timeline
2. 60/1 source -> 30/1 Timeline
3. 30000/1001 source -> 30/1 Timeline
4. every BAI_AUTO keep range has source video
5. every BAI_AUTO keep range has linked source audio where track inspection is available
6. replay -> `ALREADY_APPLIED`
7. Timeline count unchanged on replay
8. partial state rejected
9. hash conflict rejected
10. linked-A/V semantic probe remains PASS

## 7. Next gate

After linked source A/V native validation, proceed immediately to TASK-010 subtitle semantic native validation. Method presence or a truthy import return alone is not sufficient evidence that subtitle cues exist at the intended Timeline positions.
