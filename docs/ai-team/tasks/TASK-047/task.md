# TASK-047 — OBS Voice Capture Integration

- Status: `OWNER_P0_PRODUCTION_RECORDING_DEPENDENCY / P_OBS_0_DESIGN_PROBE_SEPARATE / P_OBS_1_IMPLEMENTATION_NOT_AUTHORIZED / P_OBS_2_LATER`
- Authorization: `OWNER_DIRECTED_ROADMAP_AND_DESIGN`
- Governance: `DEV-4 FOUNDATION CRITICAL`
- Dependencies: `TASK-046`, `TASK-006/023`, `TASK-020`, `TASK-043`, `TASK-045`

## Goal

Provide the minimum auditable OBS capture path required before production
training-material recording. Capture uses the Owner's explicitly selected OBS
audio input without altering the broadcast signal. The Plugin copies bounded
PCM and minimal metadata through authenticated local IPC; Dataset decisions and
all heavy analysis remain outside the real-time callback.

## Slices

### P-OBS-0 — exact target read/design/probe

- target root:
  `E:\SteamLibrary\steamapps\common\OBS Studio\bin`;
- Ver.1.2 executable baseline:
  `E:\SteamLibrary\steamapps\common\OBS Studio\bin\64bit\obs64.exe`;
- exact installed OBS build/version/architecture, executable/module inventory
  and hashes at the target root;
- separately acquired official OBS SDK/Plugin Template source reference,
  commit/version, headers, documentation and license identity; the installed
  `bin` tree is never treated as proof that SDK headers are present or exact;
- Plugin ABI, callback/load contract, WebSocket/control-plane capability,
  local IPC, synthetic compile contract, toolchain/build reproducibility,
  signing/distribution and GPL/notice review;
- read-only host inspection and synthetic contracts only;
- no Plugin load/install, OBS launch/configuration, audio capture or private
  body persistence.

P-OBS-0 may be moved forward after its contract and exact Allowed Files/
operations are separately authorized. This Task document does not grant that
implementation/probe Authorization.

### P-OBS-1 — minimum production capture MVP

- implementation may start only after the hosted contracts identify the
  existing `owner_narration.VoiceProfile`, P-VS-1A `VoiceProfileRevision`,
  TASK-046-owned `VoiceRecordingSession`/segment/Dataset-candidate/adoption
  boundary and TASK-043-owned durable recovery binding;
- explicit user selection of one Owner audio input;
- durable capture session and immutable segment identities;
- start, pause, resume and stop with a continuously visible recording state;
- the OBS real-time callback only copies bounded native frames and minimum
  metadata into a non-blocking ring/IPC boundary; it performs no resampling,
  bit-depth conversion, analysis, encryption or filesystem write;
- a bounded non-real-time worker validates and converts native frames into
  canonical `48 kHz / 24-bit / mono` raw immutable staging while preserving an
  exact source-frame-to-canonical-sample mapping and conversion Evidence;
- monotonic/source timestamps, exact frame/sample counts, missing-sample,
  overrun/drop and device/build identity Evidence;
- bounded callback/ring-buffer work and authenticated local IPC;
- crash/restart recovery with incomplete/UNKNOWN segments never promoted;
- explicit Human review before any Dataset adoption;
- no automatic Dataset adoption and no automatic training start.

P-OBS-1 owns capture/session transport and raw staging Evidence. It does not
own the Dataset store, Dataset adoption or VoiceProfile revision truth.

P-OBS-1 hosted completion is the P0 technical dependency for P-VS-3
production recording. Real recording still requires P-OBS-0 exact-path PASS,
recording Consent, verified encrypted storage and explicit Owner GO.

### P-OBS-2 — later breadth

Continuous meeting/live auto-capture, multiple Sources, speaker separation and
advanced learning proposals remain later. They are not required for the first
production-recording Gate. Other-speaker capture, automatic Dataset adoption
and online/automatic training remain prohibited.

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
- Production capture cannot begin from this roadmap/design change alone.

## Exit criteria

P-OBS-0 exact target/SDK/ABI/License/Build Evidence and P-OBS-1 selected-source
session/segment capture, pause/resume, bounded backpressure/drop Evidence,
device/mute/disconnect recovery, encrypted immutable staging, crash/restart and
review-before-adoption pass on the exact supported OBS build. Private audio,
body and machine-path data is absent from public Evidence. P-OBS-2 completion
is not required for this Gate.
