# TASK-010 Project Rate Adoption + Edit-aware Subtitle Assembly Detailed Design

- Date: 2026-08-13
- Status: IMPLEMENTATION CANDIDATE
- Parent: TASK-010 Resolve Assembly MVP
- Native evidence basis: Resolve 21.0.2.4 / Windows

## Native findings

Five product-created `BAI_AUTO_*` Timelines inherited the current Resolve Project setting of 24 fps. Resolve behaved correctly; the product defect was compiling the TASK-010 Plan as 30 fps without adopting/validating Project `timelineFrameRate`.

Timeline-local post-create `SetSetting("timelineFrameRate", "30")` returned `False`. On an empty Project before media/timeline creation, `Project.SetSetting("timelineFrameRate", "30")` returned `True`, and the next Timeline inherited 30. Existing Projects are therefore never silently changed; their Project rate is Source of Truth.

## Runtime rate contract

- Existing Project: read `timelineFrameRate`, compile Plan with that rate, and reject any mismatch before Resolve mutation.
- BAI-managed fresh Project: a desired Project rate may be set only before media/timeline creation, then re-read.
- New `BAI_AUTO_*` Timeline rate is re-read and must equal the Plan rate before media placement continues.
- `timelinePlaybackFrameRate` is not treated as TASK-010 canonical edit timebase; its render semantics belong to TASK-011 native render validation.

## Subtitle route

Native route evidence selected:

`Reviewed SRT -> edit-aware derived SRT -> MediaPool.ImportMedia -> AppendToTimeline`

`Timeline.ImportIntoTimeline(SRT)` and `MediaPool.ImportTimelineFromFile(SRT)` are rejected for this target Resolve build.

## Edit-aware cue policy

- wholly in keep range: deterministic remap
- wholly removed by approved cuts: `DROP_CUT`
- intersects/crosses a cut boundary: fail closed for Human re-review
- split across multiple kept ranges: no silent duplication
- subtitle track > 1: native-unverified and fail closed in this slice

Assembly Plan v1.2.0 stores cue ID, source frame range, target frame range, action and subtitle text SHA-256, but not raw subtitle text. Reviewed SRT content/timing is revalidated before Resolve mutation and a derived SRT is written only to an explicit managed path.

After append, TASK-010 verifies Track count, cue count, Start/End relative to Timeline start, and GetName text SHA-256. PASS requires semantic timing and text equality.
