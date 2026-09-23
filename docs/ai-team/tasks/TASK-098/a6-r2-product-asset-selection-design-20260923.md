# TASK-098 A6-R2 Product Asset Selection Integration Repair

Date: `2026-09-23`
Status: `APPROVED OWNER SCOPE / IMPLEMENTATION ALLOCATED`
Development depth: `DEV-3 HIGH ASSURANCE`

## Authority and repair finding

The Owner's A6 authority requires the verified WAV review Runtime to be usable
from the normal BAI Video Production Product/Shell after a Human operation.
A6-R1 correctly connected the Runtime, confirmation protocol and Shell display,
but the normal packaged entry chain never supplied its private A4 binding
provider.  Only tests or another Python caller could activate the connection.

A6-R2 repairs that integration gap without weakening the A6-R1 safe default.
The normal Product may create an ephemeral private binding only after a Human
selects one already canonical, currently reviewable Audio Workspace Candidate.

## Canonical boundary

- TASK-041 Audio Workspace remains the only source of currently reviewable
  `ACCEPTED` or `LOCKED` audio Candidate identity.
- The Product `SQLiteProductStore` remains the only Asset registry and rights
  authority.  `LogicalPathResolver` remains the only host-file locator.
- Selection is process-local and non-canonical.  It creates no second Asset,
  Candidate, workspace, review or receipt store.
- The selection request contains only `candidate_id`.  Asset ID, digest,
  logical URI, host path and WAV facts are resolved inside Python.
- A selected Candidate is rebound to the exact TASK-041 production/audio
  snapshot, Asset/job/checksum/rights and bounded WAV header facts.  Any change
  makes the selection unavailable and requires another Human selection.
- The A4 policy, source, capability, intent and empty timing workspace are
  deterministic, body-free, process-local records.  They authorize only the
  existing bounded local audition/waveform request and cannot claim TASK-041
  completion, Human review decision or persistence.

## Human-only protocol

1. Audio Workspace displays a review action only for a currently reviewable
   Candidate and only when the normal Product selector is bound.
2. Human selection validates the current Candidate and canonical Asset, then
   reads only the WAV container header needed to bind exact sample rate,
   channels and duration.  It does not decode samples, build a waveform or
   start playback.
3. The existing A6-R1 prepare step creates a one-use confirmation for the
   selected exact request.
4. Existing `window.confirm` remains the only playback/waveform execution gate.
5. Apply rebinds the same Candidate/Asset/snapshot and the concrete Runtime
   independently verifies the full file checksum, WAV facts and sample range
   before any playback.

Default launch, page refresh, Audio Workspace open and selection-list rendering
perform no playback, waveform generation, canonical mutation or private audio
body read.  Before Human selection the existing Shell ViewModel shape remains
unchanged and Universal WAV Review remains disabled.

## Bounds

- Review range begins at sample zero and is capped by source duration,
  30 seconds and the existing decoded-byte ceiling.
- Accepted Asset types remain `AUDIO`, `BGM` and `SFX`.
- Accepted rights remain `OWNED`, `LICENSED` and `PERMISSION_GRANTED`.
- WAV remains uncompressed PCM at exactly 48 kHz with the existing runtime
  channel/sample-width limits.
- Selection expires after the existing one-hour observation-age bound and is
  cleared on Product launch close.

## Atomic Unit and allowed files

May modify:

- this design and bounded TASK-098 Evidence/current-state records;
- `src/ai_video_production/task098_product_review_binding.py` (new);
- `src/ai_video_production/task036_trusted_launcher.py`;
- `src/ai_video_production/task036_shell_ui.py`;
- `src/ai_video_production/task098_shell_html.py`;
- exact TASK-098/TASK-036 tests for this repair.

Must not modify schemas, Asset/Audio Workspace stores, ingest, TASK-041 review
decision/completion, launch configuration, packaging/installer/version,
ASR/model settings, training, Release, Deploy or Production activation.

## Acceptance

1. Normal trusted launch owns the selector/application but performs no media
   effect and does not add a review projection before Human selection.
2. Only an exact current Audio Workspace Candidate can be selected; forged,
   cross-job, stale-snapshot, missing, wrong-digest, wrong-rights and unsupported
   WAV cases fail closed without path/body disclosure.
3. Selection reads only bounded WAV header metadata.  Refresh does not reopen
   the file or execute the Runtime.
4. A valid selection produces an exact A4 binding and enables the existing
   prepare/confirm/apply route.  Apply still performs independent registry,
   checksum, rights, file-identity, format and range validation.
5. Selection and pending confirmations are process-local, bounded and cleared
   on close.  No receipt, completion, decision, persistence or mutation claim
   is created.
6. Focused unit/integration and relevant TASK-098/TASK-036 regression pass with
   zero unresolved Critical/High findings.

## Explicit exclusions

No automatic Asset selection or ingest, arbitrary path input, transcript/voice
body exposure, TASK-041 auto-completion, Dataset adoption, training, model or
voice-server activation, packaging/installer change, Release, Deploy or
Production use is authorized by this unit.
