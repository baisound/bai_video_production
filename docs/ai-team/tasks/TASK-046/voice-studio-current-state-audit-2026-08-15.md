# TASK-046 Voice Studio Current State Audit

Date: 2026-08-15
Repository: `baisound/bai_video_production`
Exact audit base: `244e86aaa0ea65bdba2ca35176c422bcfc30d65f`

## Git and hosted state

- fresh checkout branch: `main` before the intake branch was created;
- HEAD and `origin/main`: exact match at `244e86aaa0ea65bdba2ca35176c422bcfc30d65f`;
- status/diff: clean/empty;
- open PRs: `0`;
- PR #89: merged; exact feature head
  `dfb660e7d964ddd1d2be41641d40f7ba68d3b0d7` is an ancestor of exact main;
- PR #89 hosted checks: `9 / 9 SUCCESS`;
- post-merge main CI run `31870129622`: all six OS/Python matrix jobs PASS;
- post-merge Security: PASS;
- stable release: `v0.21.0`, published 2026-08-15;
- no package version, Tag or Release is selected by this intake.

The handoff snapshot base `35b91f29...` was older. No code or completion state
was rolled back. TASK-036 P-UX-1B is hosted-closed in Git/GitHub even though
the merge commit still describes it as local-pass/hosted-pending; this document
and the roadmap intake correct that documentation lag.

## Package integrity

- extracted package files checked: `13`;
- checksum mismatches against `FILES_SHA256.txt`: `0`;
- canonical design SHA-256:
  `82533ef5b87f352f06a950a5640d6de92bee13aa2f0bfff696dca14538c17ae5`;
- noncanonical DOCX reference SHA-256:
  `46c1a3bc5959a8c9d73e71ae78d10d7a89cabc8cc44c7bf52d2934c0e8e620c0`.

The canonical Markdown input is imported unchanged. The DOCX remains a
noncanonical source input and does not override current Product contracts.

## Governance sources

Read and reconciled:

- `PROJECT.md`;
- `docs/ai-team/current-state.md`;
- `docs/ai-team/task-index.md`;
- `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md` Ver.1.84;
- current TASK-004, 006, 013, 014, 022, 023, 026, 027, 028, 032, 033, 035,
  036, 037, 038, 041, 043, 044 and 045 records;
- the complete handoff instructions and canonical design Ver.1.2, including
  Q1–Q44 and original requirements 1–32.

`README-AI.md` is not present in the current repository. Its absence is a
repository fact, not a reason to invent or import an OS-owned context file.
`.bai-os/project.json` confirms Product ownership, Governance-only OS use and
no Product runtime dependency on BAI Development OS.

## Existing implementation truth

Already implemented/reused:

- TASK-014 `VoiceProfile`, deterministic narration planning, script-body-free
  digests, paid-execution admission and character-alignment mapping;
- ElevenLabs TTS adapter foundation, but no paid call is authorized here;
- TASK-006/023 SRT/Subtitle Workspace and FasterWhisper local ASR;
- TASK-003/037/038 immutable Asset/Candidate/Audit/LOCK/STALE foundations;
- TASK-041 audio review and TASK-026 append-only placement history;
- TASK-022 rational frame authority;
- TASK-043 durable jobs/recovery;
- TASK-044 Timeline and Export Queue;
- TASK-036 single packaged desktop Shell.

Not implemented/claimed:

- Voice Studio Product workspace or successor canonical mock;
- private Voice Dataset/recording/teleprompter/preflight stores;
- local zero-shot/fine-tune engine adapter and actual local narration;
- Japanese linguistic normalization/accent/direction/forced-alignment pipeline;
- Voice Quality Calibration;
- OBS capture plugin/local IPC;
- RX 12 capability or automation;
- managed downloadable voice runtime;
- native 60–90 second Voice vertical slice.

## Task-number audit

TASK-005, 008, 009 and 015–021 already have canonical identities and cannot be
repurposed. TASK-046 through TASK-060 had zero repository references at the
audit base. The next sequential unused numbers are therefore allocated as:

- TASK-046 — Voice Studio / Voice Dataset & Local Voice Profile;
- TASK-047 — OBS Voice Capture Integration;
- TASK-048 — Voice Quality Calibration.

Existing Task numbers and completion states remain unchanged. TASK-004 and
TASK-044 are reused and are not reopened.

## Current ordering decision

The Owner's mock authority and the new Voice top-level requirement would
conflict if the EXE were changed directly. Therefore:

1. this Roadmap/Task intake is hosted as documentation only;
2. TASK-036 P-UX-1C closes current V6.1.1 native parity;
3. a reviewed successor mock revision precedes Voice Shell implementation;
4. TASK-046/014 then advance the Japanese local/free 60–90 second zero-shot
   slice before production training-material recording breadth;
5. P-OBS-0 may receive a separate read-only exact-path probe Authorization;
6. P-OBS-1 minimum Capture MVP must be hosted before P-VS-3 production
   recording and P-VS-4 fine-tuning, together with Consent, encrypted storage
   and Owner GO;
7. P-OBS-2 meeting/live continuous and multi-source breadth, RX, broad Creative
   AI and multilingual work remain later.

This is a 2026-08-15 Owner priority amendment. It does not change the original
audit facts or authorize OBS mutation/capture.
