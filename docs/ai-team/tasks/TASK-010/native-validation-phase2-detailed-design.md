# TASK-010 Native Validation Phase 2 Detailed Design

## 1. Purpose

This phase converts TASK-010 from API-capability evidence into actual editing-path evidence on Windows + DaVinci Resolve.

The previous sandbox capability gate proved that the Resolve scripting root, Project access, Project save/snapshot, Media Pool import, Timeline creation, Timeline append and markers operate in the native environment. Phase 2 must prove the product-specific `ResolveAssemblyService` / `ResolveScriptingAssemblyAdapter` path itself.

This document does **not** upgrade the Unified Desktop Application integration state. It is a backend/native acceptance gate only.

## 2. Safety floor

Native mutation is allowed only when all of the following are true:

1. the caller supplies an explicit `BAI_CAPABILITY_PROBE_*` Project name;
2. the current Resolve Project name is readable;
3. the current Project name exactly equals the authorized sandbox name;
4. the existing mutation authorization guard accepts the request;
5. generated sources and JSON Evidence remain under the supplied Evidence root;
6. no Project deletion, normal client Project mutation, Resolve termination, relink, or render cancellation is performed.

A mismatch is a hard security failure.

## 3. Acceptance matrix

Phase 2 uses three generated A/V source cases:

| Case | Source FPS | Timeline FPS | Source duration | Approved cut | Expected keep duration |
|---|---:|---:|---:|---:|---:|
| SRC30_TL30 | 30/1 | 30/1 | 4 s | 1–2 s | 3 s |
| SRC60_TL30 | 60/1 | 30/1 | 4 s | 1–2 s | 3 s |
| SRC30000_1001_TL30 | 30000/1001 | 30/1 | 4 s | 1–2 s | 3 s |

Each case must:

- generate a real MP4 source with video and audio;
- verify the generated source FPS through ffprobe;
- build a human-approved TASK-007 Edit Plan;
- compile a deterministic `BAI_AUTO_*` TASK-010 Assembly Plan;
- execute the real Resolve scripting adapter;
- verify the deterministic assembly marker;
- replay the same plan and receive `ALREADY_APPLIED`;
- prove replay does not increase Timeline count.

Fresh acceptance requires first execution `APPLIED`. `--allow-replay-only` exists only for diagnostics after a prior successful run.

## 4. Fail-closed native gates

Two additional isolated deterministic Timelines are created inside the sandbox.

### 4.1 Partial Timeline gate

A deterministic Automation Timeline exists without a trusted assembly marker.

Expected result:

`ERR_RESOLVE_PARTIAL_AUTOMATION_TIMELINE`

No append is permitted.

### 4.2 Hash-conflict gate

A deterministic Automation Timeline contains `BAI AUTO ASSEMBLY` with a different SHA-256 marker.

Expected result:

`ERR_RESOLVE_AUTOMATION_TIMELINE_HASH_CONFLICT`

No append is permitted.

## 5. Source audio preservation finding

The current TASK-010 adapter explicitly supplies `mediaType=1` for source placements. That is a video-only request.

For the minimum editing workflow, source audio preservation must be resolved before TASK-011 can require an audio stream from a real Resolve render.

Phase 2 therefore includes a bounded linked-A/V semantic probe that imports the same generated A/V source and calls `AppendToTimeline` **without** `mediaType`. It then inspects returned item track metadata and Timeline video/audio track contents where the installed Resolve build exposes those queries.

This probe does not change product behavior. It creates Evidence for the next design decision:

- if both video and audio are observed, design a `PRESERVE_LINKED_AV` source-placement mode and native-validate it;
- if audio is not observed, design an explicit paired video/audio placement path and validate source/audio trim semantics separately;
- if the installed API cannot semantically verify the result, retain the issue as unresolved and do not claim minimum editing completion.

## 6. Evidence output

The harness writes a JSON report under the supplied Evidence root. Persisted data contains:

- Resolve version/product name;
- sandbox Project name;
- case IDs and rational frame rates;
- generated source filename, hash, size and ffprobe timing metadata;
- Edit keep ranges;
- expected Timeline duration frames;
- first/replay assembly reports;
- Timeline marker verification and available track counts;
- partial/conflict negative-gate results;
- linked-A/V semantic-probe result;
- no host absolute paths.

Overall status may be:

- `PASS`
- `PASS_WITH_FINDING` when the core TASK-010 gate passes but linked-A/V semantics remain unresolved
- `FAIL`

## 7. Next development immediately after Phase 2

### 7.1 TASK-010 source A/V preservation

Implement the smallest behavior supported by the native linked-A/V probe. Required tests:

- 30 → 30 trim;
- 60 → 30 trim;
- 30000/1001 → 30 trim;
- linked source audio retained for every keep range;
- idempotent replay;
- partial state rejection;
- hash conflict rejection;
- human/non-automation Timeline protection unchanged.

### 7.2 TASK-010 subtitle native gate

Use a reviewed SRT and validate `Timeline.ImportIntoTimeline` semantically on the actual `BAI_AUTO_*` Timeline. Method presence alone is insufficient.

### 7.3 TASK-011 real render artifact gate

After TASK-010 produces a real A/V Timeline:

1. perform a sandbox render;
2. verify non-empty artifact;
3. verify required video/audio streams;
4. verify exact rational duration within tolerance;
5. run loudness/true-peak analysis;
6. preserve the TASK-011 report.

Render queue orchestration remains a separate capability from `RenderQAService`; do not claim product render automation until it is explicitly implemented and accepted.

### 7.4 TASK-012 EDITOR_WORK native gate

Using the passing render:

1. create deterministic `EDITOR_WORK_*`;
2. copy the Render QA report and Resolve assembly result;
3. include a retained `.drp` snapshot;
4. export a 48 kHz PCM WAV for Cubase round-trip;
5. accept a valid 48 kHz return;
6. reject a 44.1 kHz return;
7. verify render re-hash protection.

### 7.5 Unified client slice

Backend/native acceptance still does not equal product UX completion. After the backend gate closes, expose the minimum workflow through the Unified Desktop Application and execute the full Windows E2E path without PowerShell/JSON as the final user-facing acceptance gate.
