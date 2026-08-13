# TASK-011 — Native Resolve Render Queue / Real Artifact QA Gate Ver.1.0

- Date: 2026-08-13
- Depends on: TASK-010 Automation-owned `BAI_AUTO_*` Timeline
- Scope: native backend validation only
- Product completion claim: prohibited by this document

## Objective

Close the gap between the existing `RenderQAService` (which can validate a file) and a real Resolve workflow by proving:

`TASK-010 Timeline -> Resolve Render Queue -> completed native render -> real artifact -> ffprobe/ffmpeg QA -> path-free Evidence`.

## Safety contract

1. A real render requires explicit runtime authorization (`--authorize-resolve-render`).
2. The current Resolve Project must exactly match an explicitly named `BAI_CAPABILITY_PROBE_*` sandbox.
3. The target Timeline must be an exact deterministic `BAI_AUTO_<12HEX>` Timeline and must resolve uniquely.
4. Human-owned Timelines are not created, renamed, deleted or modified by this gate.
5. Render output is a dedicated empty Evidence directory; pre-existing output fails closed.
6. Absolute render paths and render job IDs are not persisted in the native Evidence report.
7. The gate leaves the active Project render preset unchanged unless an explicit format+codec pair is provided together.
8. Render timeout is bounded; if Resolve exposes `StopRendering`, timeout attempts a stop before failing.
9. Quality misses are represented by TASK-011 QA status; API/state ambiguity raises structured ProductError.
10. No release, tag, deployment or user-facing completion is implied.

## Native linkage

The preferred CLI input is the persisted TASK-010 assembly plan. The gate reads only:

- `task_owner=TASK-010`
- `timeline_name`
- `expected_duration_frames`
- `assembly_sha256`

This prevents a manual duration/timeline typo from silently validating the wrong timeline. Direct timeline/duration arguments remain diagnostic fallback.

## Resolve API surface

Bounded calls:

- `GetProjectManager`
- `GetCurrentProject`
- `GetTimelineCount` / `GetTimelineByIndex`
- `SetCurrentTimeline`
- `GetSetting("timelineFrameRate")`
- optional `SetCurrentRenderFormatAndCodec`
- `SetRenderSettings`
- `AddRenderJob`
- `StartRendering(jobId)`
- `IsRenderingInProgress`
- `GetRenderJobStatus(jobId)`
- timeout-only `StopRendering`

The gate intentionally does not delete Render Queue jobs automatically because deletion would introduce another external mutation and can remove useful native inspection state.

## Artifact acceptance

The dedicated output directory must contain exactly one non-empty regular non-symlink file. TASK-011 then verifies:

- video stream
- audio stream
- duration against exact Resolve Project timeline rate
- configurable integrated loudness
- configurable true peak
- optional LRA
- artifact SHA-256/size

## Evidence

Native report contains the sandbox name and deterministic Timeline identity because both are deliberate test identities. It does not persist:

- host absolute render path
- render job UUID
- credentials

## Automated acceptance before Windows native run

- missing explicit authorization rejected before mutation;
- wrong Project rejected before render settings;
- missing/ambiguous Timeline rejected;
- non-empty target rejected before queue mutation;
- ambiguous artifact rejected;
- NTSC `29.97 -> 30000/1001` conversion pinned;
- TASK-010 plan linkage pinned;
- path-free report pinned.

## Native Windows acceptance still required

Run against a fresh isolated Resolve sandbox using an already native-validated TASK-010 Timeline. `NATIVE_VALIDATED` may be recorded only when the actual installed Resolve/ffprobe/ffmpeg path produces PASS Evidence.
