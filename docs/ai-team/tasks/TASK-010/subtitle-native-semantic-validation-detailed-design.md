# TASK-010 Subtitle Native Semantic Validation Detailed Design

- Date: 2026-08-13
- Status: IMPLEMENTATION CANDIDATE
- Parent: TASK-010 Resolve Assembly MVP
- Prerequisite: linked source A/V native validation PASS
- Product architecture: PRODUCT-ARCH-001

## 1. Problem

`Timeline.ImportIntoTimeline(SRT)` returning a truthy value proves only that Resolve accepted the call. It does not prove that reviewed subtitle cues exist on the intended Automation Timeline at the intended timing.

The native gate must inspect actual post-import Timeline state.

## 2. Fixture

Use an approved two-cue Subtitle Workspace:

- `native-sub-001`: 00:00:00.250 -> 00:00:00.750
- `native-sub-002`: 00:00:02.250 -> 00:00:02.950

The Workspace is compiled through the real TASK-006 `ResolveSubtitleHandoffService` at 30 fps and passed into real TASK-010 `ResolveAssemblyService`.

## 3. Automated semantic checks

After execution the gate attempts to inspect:

- `Timeline.GetTrackCount("subtitle")`
- `Timeline.GetItemListInTrack("subtitle", track)`
- each subtitle item's `GetStart()`
- each subtitle item's `GetEnd()`
- optionally `GetName()` for text

Timing comparison is performed relative to `Timeline.GetStartFrame()` so the gate does not assume a zero Resolve start timecode.

A PASS cannot be produced from `ImportIntoTimeline` method presence or a truthy import return alone.

## 4. Text verification

If the installed Resolve build exposes subtitle text through `TimelineItem.GetName()` and exact fixture text matches, text is automatically verified.

If timing/count are verified but text cannot be read semantically through the scripting API:

`HUMAN_REVIEW_REQUIRED`

A second replay may be run with explicit:

- `--human-confirm-text`
- `--human-reviewer-id`

The deterministic Timeline should then be reused rather than duplicated. Human confirmation closes only text verification; it cannot override a timing failure.

## 5. Outcomes

- `PASS`: track/item/timing semantics proven and text proven automatically or explicitly by Human review
- `HUMAN_REVIEW_REQUIRED`: placement/timing proven, text inaccessible or not automatically proven
- `FAIL`: track/item/timing semantics not proven

## 6. Safety

- mutation only in exact `BAI_CAPABILITY_PROBE_*` Project
- reviewed Workspace only
- explicit TASK-010 external write authorization
- deterministic BAI_AUTO Timeline
- existing idempotency / partial-state / conflict protections remain active
- Evidence persists no host absolute paths

## 7. Next route

After subtitle semantics PASS:

1. TASK-011 sandbox Render Queue capability and orchestration gate
2. real render artifact
3. RenderQAService: streams, duration, loudness, true peak
4. TASK-012 EDITOR_WORK / Cubase return native gate
