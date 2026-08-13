# TASK-041 — Audio Workspace / Embedded Audio Separation & Placement UX
## Pre-implementation Detailed Design Ver.0.9

- Date: 2026-08-13
- Status: `DESIGN_AHEAD / IMPLEMENTATION_NOT_AUTHORIZED_BY_THIS_DOCUMENT`
- Depends on: TASK-003, TASK-026, TASK-037

## Objective

Give audio the same Candidate/Review/Lock discipline as visual Assets while preserving non-destructive separation between generated media audio and picture.

## Audio slot classes

- `SOURCE_AUDIO`
- `VFX_EMBEDDED_AUDIO`
- `SE`
- `BGM`
- `NARRATION`
- `MIX_STEM`
- `FINAL_MIX`

## Non-destructive strip policy

Removing embedded audio from a generated video never rewrites the original Asset. It creates a derived Asset with provenance:

`original candidate -> derived no-audio candidate`

The original remains traceable.

## Placement

TASK-026 owns the placement plan semantics. TASK-041 owns normal-user review UX:

- waveform/lane view;
- candidate audition;
- placement markers/ranges;
- gain/fade metadata where owned by placement contract;
- accept/reject/alternate use;
- lock;
- stale indication;
- route to NLE assembly.

## VFX policy

Visual and audio judgement remain separable:

- visual PASS + audio FAIL may produce accepted visual derivative with audio stripped;
- audio PASS + visual FAIL may retain audio for alternate use;
- no all-or-nothing destructive reject.

## External DAW

TASK-012/Cubase and TASK-035/REAPER remain bounded external handoffs. Audio Workspace should show handoff/return state but not pretend an external DAW is embedded.

## Acceptance draft

- original bytes immutable;
- strip creates derived Asset;
- audio/visual decisions independently traceable;
- placement review before Resolve write;
- locked audio candidate cannot be silently replaced;
- BGM/SE/narration provider cost authorization remains separate;
- one unified Desktop Workspace, no separate final app.
