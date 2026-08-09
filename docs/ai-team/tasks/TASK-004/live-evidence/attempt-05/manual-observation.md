# TASK-004 Live Evidence — Attempt 05

Date: 2026-08-09
Target: Owner Windows workstation
Package used: 0.4.4

## Result

Audacity/OpenVINO capability probe: **PASS**.

Returned runtime evidence:

- `connected: true`
- `ok: true`
- `current_track_count: 0`
- `NOISE_SUPPRESSION.available: true`
- `MUSIC_SEPARATION.available: true`
- `WHISPER_TRANSCRIPTION.available: true`
- `MUSIC_GENERATION.available: true`
- `AUDIO_SUPER_RESOLUTION.available: true`
- worker progress reached `EXECUTION_COMPLETE`

Each targeted `Help` descriptor returned the expected Audacity command id and OpenVINO effect name. The live descriptors expose an empty `params` array for these OpenVINO effects.

## Interpretation

The local Audacity `mod-script-pipe` boundary and all five targeted Intel OpenVINO effects are live-reachable on the target machine. This closes the capability-discovery gate.

The empty Music Separation parameter descriptor is a material runtime fact. Intel's current effect implementation initializes separation mode index 0 as `(2 Stem) Instrumental, Vocals`, while the 4-stem selector is UI state and is not exposed through Audacity's scriptable parameter definition. Product 0.4.5 therefore permits the provable no-parameter 2-stem default and fails closed for 4-stem unless a future runtime exposes a scriptable mode parameter or a separate provider is added.

No OpenVINO effect was executed by this capability attempt. Noise Suppression and 2-stem Music Separation still require synthetic behavioral Evidence before TASK-004 can close.
