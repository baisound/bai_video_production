# TASK-047 — OBS Voice Capture Integration

- Status: `P_OBS_1_PUBLIC_TECHNICAL_PREVIEW_RELEASED / OWNER_VOICE_AND_PRODUCTION_RECORDING_GATE_OPEN / P_OBS_2_LATER`
- Authorization: `OWNER_DIRECTED_ROADMAP_AND_DESIGN / OWNER_STANDING_AUG_2026_DEVELOPER2_INSTALL_ACQUIRE_CONFIGURE_BUILD`
- Governance: `DEV-4 FOUNDATION CRITICAL`
- Dependencies: `TASK-046`, `TASK-006/023`, `TASK-020`, `TASK-043`, `TASK-045`

## Canonical P-OBS-1A design contract

- Contract:
  `p-obs-1a-native-selected-source-capture-adapter-contract-rev2.1-2026-08-15.md`
- Provenance:
  `p-obs-1a-native-selected-source-capture-adapter-contract-rev2.1-provenance.json`
- Activation: design authority only when the exact contract and provenance are
  read from `main` and their digests validate.
- Implementation, native build/install/load, OBS launch/configuration/capture,
  audio/device/Asset/Dataset mutation: `NOT_AUTHORIZED`.

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
- start, pause, resume and stop while the exact selected OBS 32.2.1 process remains running;
- pause/resume/stop must validate the same OBS process ID and executable path used at start;
- show a continuously visible `学習データ録音中` / `一時停止中` state so a forgotten
  capture cannot silently consume disk or other resources;
- provide a real-time Peak/RMS GAIN meter with clipping indication before and during capture,
  without changing preamp, +48 V, PAD, HPF, OS, OBS mixer, filter or device settings;
- let the user choose the recording destination, maximum duration and free-space stop floor;
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

#### Final installation and distribution shape

The final Owner-facing installation path is an **installer**, not manual ZIP
copying. ZIP artifacts remain immutable engineering/build inputs and recovery
Evidence; they are not the final installation UX. The installer contract must:

- discover or let the Owner select the exact OBS installation without a
  machine-specific path baked into public metadata;
- verify package identity, OBS version/architecture, process state, path
  containment, reparse points, collisions, disk floor and required authority
  before making a change;
- stage and hash all payloads, create an exact pre-install backup/tombstone
  manifest and append-only journal, publish only installer-owned files, then
  read back every installed byte before claiming success;
- install the OBS plugin payload and the separate recording controller without
  copying controller files, licenses, manifests or source offers into the OBS
  plugin directories unless the deployment manifest explicitly owns that path;
- expose Repair, Update and Uninstall as distinct, confirmed transactions.
  Uninstall removes only installer-owned files; rollback restores the exact
  prior manifest and is never an automatic response to `UNKNOWN`;
- preserve Scene, Profile, Source, Filter, device, gain and recording settings
  unless a later exact Human-authorized operation owns those changes;
- keep install completion separate from module load, recording, Dataset,
  Training, Release and production admission;
- include the installer, matching runtime/source ZIPs and SHA-256 manifest in the public
  GitHub Technical Preview Release, and provide beginner-friendly Japanese and English
  installation, build, recording, pause/resume, save and recovery guidance reachable from
  the repository README;
- carry exact version/hash, notices, source-offer and signing/admission Evidence.
  Code-signing and publisher UX remain a Release Gate; a local unsigned test
  package is not presented as a production installer.

The local technical candidate uses Inno Setup 7.1.0 in per-user mode and keeps
the OBS installation selectable. Clean install, same-version repair, collision
refusal, verified uninstall, preexisting exact3 restore and append-only journal
hash-chain behavior passed on a synthetic OBS root; the exact OBS 32.2.1 target
also passed installer-managed migration and module-load read-back. Code signing,
publisher identity, public distribution and destructive interrupted-publish
testing remain separate Gates. A future release-grade installer test must retain
clean install, existing-version
repair, version update, collision refusal, interrupted/`UNKNOWN` reconciliation,
verified uninstall and verified rollback on the exact supported OBS build.

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
- Final Owner-facing deployment is installer-based. Manual ZIP extraction and
  exact-file copying are development/recovery procedures only.
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
