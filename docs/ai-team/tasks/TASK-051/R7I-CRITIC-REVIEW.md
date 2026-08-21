# TASK-051 R7I — Critic Design and Implementation Review

## Review profile

- Profile: `DEV-3 HIGH ASSURANCE`
- Review scope: workflow responsibility, media commonization, audio lifecycle, Fit-to-View, training evidence integrity, migration compatibility, background thread/Tk ownership and tests.

## Findings

### Critical

`0`

### High

`0` after implementation corrections.

### Medium

`0` blocking.

## Positive findings

- Batch and single-image video learning now share a final visual registration contract while preserving distinct operator workflows.
- Media playback is commonized instead of fixing five screens independently.
- All twelve transport actions remain owned by one `BUTTON_LAYOUT` contract.
- Audio is bounded to normal playback and is explicitly stopped for seek/rewind/fast-forward, avoiding an unreviewed time-stretch subsystem.
- Fit-to-View is treated as an interaction requirement; form overflow is solved by scrolling, not source Crop.
- Exact teacher-data extraction remains independent from display-preview dropping/coalescing.
- R7H's Tk-main-thread ownership rule is preserved and generic background jobs no longer call `root.after` from the worker.
- Visual registration schema additions are backwards-compatible, and relabel preserves the new provenance fields.
- Batch range candidate growth is bounded by total Crops across frames x selected targets.

## Accepted conditions

- `ffplay` is an external runtime companion to the existing FFmpeg toolchain and must be available on the Windows Human Acceptance machine. Missing ffplay is fail-visible, not silent.
- Rewind/fast-forward audio remains intentionally muted in R7I.
- Real Windows/DPI/audio/packaged behavior cannot be promoted to PASS from Linux/source tests.

## Decision

`PASS_WITH_WINDOWS_HUMAN_ACCEPTANCE_REQUIRED`

R7I is suitable for bounded Windows acceptance. Local verification is `317 PASS / 1 display-only SKIP` for TASK-049/050/051 and sharded full-repository `2283 PASS / 2 environment-only SKIP`; accepted-source synchronization is complete. TASK-051 completion remains unauthorized until the real-media Human Acceptance blocker set is zero.
