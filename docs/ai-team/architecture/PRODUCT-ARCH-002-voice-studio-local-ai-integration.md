# PRODUCT-ARCH-002 — Voice Studio and Local AI Integration

Date: 2026-08-15
Status: `PROPOSED_CANONICAL / HOSTED_CLOSURE_PENDING`
Exact base main: `244e86aaa0ea65bdba2ca35176c422bcfc30d65f`

## Decision

Voice Studio is a first-class capability of the single BAI Video Production
desktop product, not a separate user-facing application. Product Core owns
identity, consent, revision, job, Asset, Timeline and decision truth. Local
voice engines, OBS, REAPER/RX, Resolve and optional Cloud providers are bounded
adapters and never become canonical databases.

```text
Approved Japanese SRT / Voice text revisions
                    +
Private VoiceProfile / Consent / Model-License revision
                    ↓
TASK-014 Local Narration Job
                    ↓
48 kHz staged WAV + measured alignment/duration
                    ↓
TASK-003 Asset → TASK-037 Candidate → TASK-041 Human review
                    ↓
TASK-026 Placement → TASK-022 exact frames → TASK-044 Timeline/Export
```

## Authority map

| Truth | Owner |
|---|---|
| Voice Dataset, VoiceProfile and recording review | TASK-046 |
| OBS capture candidate | TASK-047 |
| calibrated quality profile/trace | TASK-048 |
| narration plan/render/publication | TASK-014 |
| subtitle source/display revisions | TASK-006 |
| local ASR provider | TASK-023 |
| canonical Asset and rights | TASK-003 |
| Candidate/LOCK/STALE | TASK-037/038 |
| Human audio review | TASK-041 |
| audio placement and exact frames | TASK-026/022 |
| durable Product jobs/recovery | TASK-043 |
| Timeline and Export Queue | TASK-044 |
| packaged Shell/native UI | TASK-036 |
| resource admission | TASK-020 |
| optional finishing | TASK-035 |

## Non-negotiable data rules

- Subtitle Text, Normalized Text, TTS Text and Alignment Text are separate,
  revisioned representations linked by Scene/Cue identity.
- Canonical timing is TASK-022 rational frame placement. Milliseconds are an
  adapter/display projection only.
- Raw recording, processed audio, generated Take, canonical 48 kHz narration
  and finished audio are distinct immutable Assets/Revisions.
- Model, code, checkpoint, adapter, reference, Dataset and output licenses are
  independently evidenced; restrictions monotonically propagate to derived
  Assets, Timeline candidates and Export.
- UNKNOWN identity, consent, license or external execution state fails closed.
- Local Primary never silently falls back to Cloud or CPU. Paid/Cloud paths
  show provider, transmitted data, retention and estimate before each GO.

## Privacy and recovery

Private voice material uses Product-managed envelope encryption. OS-protected
keys and an explicitly created password recovery package are separate. Public
Evidence excludes raw audio, body text, voice IDs, embeddings, credentials and
machine-specific paths. Durable jobs checkpoint before side effects, retain
completed Cue hashes, and never auto-replay UNKNOWN external work.

## Shell design rule

The current V6.1.1 mock remains absolute authority through P-UX-1C. Adding a
Voice Studio top-level destination requires a reviewed successor canonical
mock revision first. The implementation must preserve the existing visual
language, interaction intent and single-EXE entrypoint; a second launcher or an
EXE-only layout invention is prohibited.

## Delivery order

1. Host this architecture/roadmap intake.
2. Complete TASK-036 P-UX-1C against the unchanged V6.1.1 mock.
3. Approve a successor canonical mock for the Voice Studio destination.
4. Implement TASK-046 P-VS-1 non-executing foundation.
5. Establish exact local model/runtime/license evidence.
6. Run the Japanese owner-only local/free 60–90 second vertical slice.
7. Add recording/fine-tuning/calibration, then OBS and optional finishing.
8. Add broader Local Creative AI/Managed Runtime and locale gates only after
   the vertical slice is traceable and recoverable.
