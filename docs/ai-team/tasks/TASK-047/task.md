# TASK-047 — OBS Voice Capture Integration

- Status: `FORMALLY_ALLOCATED / DESIGN_QUEUED_AFTER_TASK_046_VERTICAL_SLICE`
- Authorization: `OWNER_DIRECTED_ROADMAP_AND_DESIGN`
- Governance: `DEV-4 FOUNDATION CRITICAL`
- Dependencies: `TASK-046`, `TASK-006/023`, `TASK-020`, `TASK-043`

## Goal

Capture the Owner's explicitly selected OBS microphone source as reviewable
Voice Studio candidates without altering the broadcast signal. The OBS plugin
copies bounded PCM and minimal metadata through authenticated local IPC; VAD,
speaker verification, ASR, quality analysis and Dataset decisions run outside
the real-time audio callback.

## Permanent boundaries

- Windows 11 x64 and OBS 32.2.1 are a probe baseline, not a compatibility
  claim. Exact ABI/load/callback/IPC behavior must be re-probed after updates.
- Owner microphone is the only initial formal subject. Other speakers, mixed
  meetings, BGM and game audio are quarantined or rejected by default.
- Recording is visible, consent-bound and independently stoppable. Automatic
  recording never means automatic Dataset adoption or training.
- OBS audio is never modified by the capture filter.
- The OBS-linked plugin and Product Core stay separated by local IPC; GPL
  linkage, source publication, notices, signing and distribution require a
  dedicated legal/release decision.
- No real OBS configuration or Project is changed by design authorization.

## Exit criteria

Selected-source capture, pause/resume, bounded backpressure/drop Evidence,
device/mute/disconnect recovery, Owner-speaker quarantine and Human Dataset
adoption pass on the exact supported OBS build. Private audio/body/path data is
absent from public Evidence.
