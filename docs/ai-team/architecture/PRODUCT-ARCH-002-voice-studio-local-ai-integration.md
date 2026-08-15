# PRODUCT-ARCH-002 — Voice Studio and Local AI Integration

Date: 2026-08-15
Status: `CANONICAL / P_VS_1A_PARALLEL_LOCK_ACTIVE / P_VS_1B_MOCK_GATED / P_OBS_1_PRODUCTION_RECORDING_P0_GATE`
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
| Voice Dataset, VoiceProfile, recording review and Dataset adoption | TASK-046 |
| OBS selected-input capture session, raw immutable staging and capture recovery Evidence | TASK-047 |
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

1. Retain the P-VS-0 architecture/roadmap intake hosted by PR #90 at exact
   main `25e2e04fb3360af77017a4a42e868fc95b15ec80`.
2. Host and read the disjoint P-UX-1C/P-VS-1A Work Lock Registry.
3. Complete TASK-036 P-UX-1C against the unchanged V6.1.1 mock while P-VS-1A
   may develop only its Shell-independent, body-free, non-executing Backend on
   a separate fresh-main branch.
4. After P-UX-1C hosted closure, rebase and merge P-VS-1A with overlap `0`.
5. Approve a successor canonical mock for the Voice Studio destination, then
   separately authorize P-VS-1B Shell/TASK-014 integration.
6. Establish exact local model/runtime/license evidence.
7. Run the Japanese owner-only local/free 60–90 second vertical slice.
8. Separately authorize P-OBS-0 read-only installed-target inventory plus
   official SDK/Plugin Template identity/ABI/License/Build probe; it may move
   earlier after its contract is closed.
9. Host P-OBS-1 minimum selected-input Capture MVP before any P-VS-3
   production training-material recording.
10. Require P-OBS-1 hosted completion, exact-path probe PASS, recording
   Consent, encrypted storage and Owner GO before P-VS-3 recording and P-VS-4
   fine-tuning.
11. Add calibration, P-OBS-2 meeting/live continuous and multi-source breadth,
   then optional finishing.
12. Add broader Local Creative AI/Managed Runtime and locale gates only after
   the vertical slice is traceable and recoverable.

P-VS-1A does not store voice/audio bodies and does not download, load or invoke
an Engine. Its new domain type is `VoiceProfileRevision`; the existing
`owner_narration.py::VoiceProfile` remains the canonical narration identity and
must not be duplicated. P-VS-1B remains blocked by the successor-mock and separate
Authorization gates. The hosted architecture therefore describes a future
runtime boundary; it does not claim Voice Studio runtime implementation.

## Production recording gate

P-VS-2 is a zero-shot Product vertical slice and does not authorize collection
of new production training material. P-VS-3 may define recording/session
contracts and synthetic fixtures early, but real production capture requires
all of the following:

- P-OBS-1 hosted minimum Capture MVP completion;
- P-OBS-0 PASS against
  `E:\SteamLibrary\steamapps\common\OBS Studio\bin` and the exact supported
  OBS executable/SDK/ABI/License/Build identity;
- explicit recording Consent for the selected Owner input and purpose;
- verified envelope-encrypted immutable raw staging and recovery boundary;
- explicit Owner GO for the bounded Session.

P-OBS-1 records no automatic Dataset decision. TASK-046 Human review must
explicitly adopt eligible segments; adoption never starts training. P-OBS-2
continuous meeting/live capture, multiple Sources and advanced proposals are
later breadth and are not required for the first production-recording Gate.

P-OBS-0 separates installed-target truth from development-source truth. The
exact `bin` root proves only the installed executable/module inventory,
versions, architecture and hashes. Official SDK/Plugin Template headers,
documentation, source reference/commit and license identity require their own
authorized acquisition and Evidence; they are not inferred from the install
tree.

Before P-OBS-1 implementation, hosted contracts must bind the existing
`owner_narration.VoiceProfile`, the P-VS-1A `VoiceProfileRevision`,
TASK-046-owned `VoiceRecordingSession`/segment/Dataset-candidate/adoption truth
and TASK-043-owned durable recovery truth. The OBS real-time callback may only
copy bounded native frames and minimum metadata through a non-blocking
boundary. Canonical 48 kHz/24-bit/mono validation/conversion, encryption,
analysis and persistence run outside the callback with exact source-to-output
sample lineage.
