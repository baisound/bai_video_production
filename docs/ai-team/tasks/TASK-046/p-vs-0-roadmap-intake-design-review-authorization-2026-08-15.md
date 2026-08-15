# TASK-046 P-VS-0 Roadmap Intake, Design Review and Authorization

Date: 2026-08-15
Exact base main: `244e86aaa0ea65bdba2ca35176c422bcfc30d65f`
Branch: `codex/task-046-voice-studio-roadmap-intake`
Unit: `DESIGN_AND_GOVERNANCE_ONLY`

## Hosted closure

- PR: `#90` / `https://github.com/baisound/bai_video_production/pull/90`
- Exact head: `664722d0fac8cc0e79f7c424c6911f4651ceb303`
- Hosted checks: `9 / 9 PASS`
- Merged: `2026-08-15T07:07:43Z`
- Exact main merge: `25e2e04fb3360af77017a4a42e868fc95b15ec80`
- Post-merge main CI: PASS, workflow `31871164920`
- Post-merge main Security: PASS, workflow `31871164981`

P-VS-0 is `HOSTED_CLOSED`. The former `HOSTED_PENDING` state is historical and
must not be used as the current Consumer route.

## Current OS audit and Source of Truth

The current BAI Video Production checkout and GitHub main are newer than the
handoff snapshot. Exact main `244e86a` is the implementation Source of Truth.
The checkout was clean, open PR count was zero, PR #89 and its 9/9 checks were
complete, and post-merge main CI/Security were green before this branch was
created. Stable release remains `v0.21.0`.

Package integrity is 13/13 with zero mismatch. The complete Ver.1.2 design,
Q1–Q44 and OR-01–OR-32 were read. TASK-004/044 completion is preserved.

## Task allocation and DEV Profile

| Task | Allocation | DEV decision |
|---|---|---|
| TASK-046 | Voice Studio / Voice Dataset & Local Voice Profile | DEV-4: biometric/private data, consent, encryption, model/runtime, irreversible training and broad cross-store lineage |
| TASK-047 | OBS Voice Capture Integration | DEV-4: real-time native plugin, private audio, consent, GPL/IPC/distribution and external application interaction |
| TASK-048 | Voice Quality Calibration | DEV-4: quality decisions can affect VoiceProfile approval and commercial export; Human authority and versioned decision trace are mandatory |

TASK-046..048 were the first three sequential numbers with zero repository
references. Reserved/not-started TASK-005, 008, 009 and 015–021 are not reused.

## Roadmap decision

The final sequence is:

1. P-VS-0 documentation-only intake and hosted closure.
2. TASK-036 P-UX-1C native parity closure against unchanged V6.1.1.
3. TASK-046 P-VS-1A Shell-independent, body-free, non-executing Voice Backend
   may develop in parallel under its hosted disjoint File Lock, but merges only
   after P-UX-1C hosted closure and fresh-main rebase.
4. reviewed successor canonical mock, followed by separately authorized
   P-VS-1B Shell/TASK-014 integration.
5. exact local voice Model/Runtime/License capability decision.
6. P-VS-2 Japanese, owner-only, Local/free 60–90 second vertical slice.
7. P-OBS-0 read-only installed-target inventory plus separately sourced
   official SDK/Plugin Template identity/ABI/License/Build probe may receive a
   separate early Authorization after its contract is closed.
8. P-OBS-1 minimum Capture MVP hosted completion.
9. P-VS-3 production recording/Dataset only after P-OBS-1, exact-path PASS,
   recording Consent, encrypted storage and Owner GO; then P-VS-4 fine-tuning.
10. TASK-048 quality calibration.
11. P-OBS-2 meeting/live continuous and multi-source breadth.
12. TASK-035 RX 12/REAPER finishing.
13. Managed Runtime, broader Local Creative AI and staged locale gates.

This moves the vertical slice ahead of breadth while preserving the existing
mock-authority route. It does not claim the native vertical slice complete.

Owner priority amendment `2026-08-15`: the original sequence that placed OBS
after production recording is superseded. P-OBS-1 is now the P0 technical
dependency for production training-material capture, but it does not itself
grant recording, Dataset adoption or training authority.

## Allowed Files — P-VS-0

- `PROJECT.md`
- `CHANGELOG.md`
- `docs/ai-team/current-state.md`
- `docs/ai-team/task-index.md`
- `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md`
- `docs/ai-team/architecture/PRODUCT-ARCH-002-voice-studio-local-ai-integration.md`
- `docs/ai-team/product-design/voice-studio/BAI_VIDEO_PRODUCTION_VOICE_STUDIO_LOCAL_AI_OBS_統合詳細設計書_Ver1.2.md`
- `docs/ai-team/tasks/TASK-046/**`
- `docs/ai-team/tasks/TASK-047/task.md`
- `docs/ai-team/tasks/TASK-048/task.md`
- `docs/ai-team/tasks/TASK-036/p-ux-1b-interaction-state-convergence-implementation-and-native-evidence-2026-08-15.md`
- bounded responsibility supplements in TASK-006, 014, 023 and 035 task files.

No `src/`, runtime, schema, package-version, release, native-app or external
Project change is allowed in P-VS-0.

## Builder design — first implementation unit P-VS-1A

After P-VS-0 and the parallel Work Lock Registry are hosted, an isolated
fresh-main P-VS-1A branch may implement only the following. Its main merge
still waits for P-UX-1C hosted closure and fresh-main rebase:

- immutable private `VoiceProfileRevision` metadata and consent/license status,
  while `owner_narration.py::VoiceProfile` remains the read-only canonical
  narration identity;
- project-local atomic/CAS store with no raw voice body in public projections;
- local engine capability interface and non-executing preflight;
- deterministic public/private projection and secret/path redaction;
- failure/restart/tamper tests using synthetic metadata only.

Tentative exact implementation files:

- `src/ai_video_production/voice_profile_revision.py`
- `src/ai_video_production/voice_profile_store.py`
- `src/ai_video_production/voice_studio_application.py`
- `schemas/voice-profile-revision.schema.json`
- `src/ai_video_production/schema_resources/voice-profile-revision.schema.json`
- `tests/test_task046_voice_profile_foundation.py`
- `docs/ai-team/tasks/TASK-046/p-vs-1a-*.md`

`src/ai_video_production/owner_narration.py` and the existing shared Product
stores are read-only dependencies. Package exports, global current-state,
Roadmap, Architecture, CHANGELOG and release files require a separate
Integration Lock and are not P-VS-1A implementation Allowed Files.

P-VS-1A excludes recording, audio body import, engine/model download, TTS,
training, OBS, RX/REAPER, Cloud/paid execution, Shell changes, external writes,
version, Tag, Release and Deploy.

## Critic Pass 1

Decision: `CHANGES_REQUIRED`.

Findings:

1. **High — canonical mock conflict.** Ver.1.2 requires a Voice Studio
   top-level destination that does not exist in V6.1.1. Direct EXE addition
   would violate the Owner's absolute mock authority.
2. **High — vertical slice was too late.** The source design's Phase 11 could
   allow broad recording/runtime work before proving one complete Product path.
3. **High — TASK-020 is not implemented.** Treating the complete scheduler as a
   prerequisite would block the first slice or encourage an unauthorized large
   implementation.
4. **High — model family names could be mistaken for approval.** Candidates
   without exact Artifact/license/runtime proof cannot become commercial paths.
5. **Medium — existing TASK-014 foundation was understated.** A second
   VoiceProfile or narration planner would duplicate current code.

Corrections:

- P-UX-1C closes V6.1.1 first; a successor canonical mock precedes Voice UI.
- The 60–90 second slice is moved immediately after the bounded foundation and
  exact runtime/license decision.
- Initial exclusive work may use a bounded TASK-043-owned lock/recovery
  contract; full resource scheduling remains TASK-020.
- Model candidates remain `CATALOG_ONLY/EVALUATION_CANDIDATE` until exact proof.
- TASK-046 reuses TASK-014 and owns only Dataset/Profile gaps.

## Critic Pass 2

Decision: `CHANGES_REQUIRED`.

Findings:

1. **High — P-VS-1A still risked implicit execution.** A local adapter interface
   could be read as permission to download or invoke a Model.
2. **High — encrypted-data claims preceded an implementation route.** Private
   voice bodies must not be persisted until the encryption/recovery contract is
   implemented and verified.
3. **High — native vertical slice authority was ambiguous.** Actual Owner voice
   processing, Model installation and external app mutation require their own
   exact gates.
4. **Medium — multilingual labels were too broad.** UI translation alone cannot
   satisfy Chinese/Taiwan/Korean/English product support.

Corrections:

- P-VS-1A is explicitly non-executing and body-free; exact model download and
  invocation are excluded.
- Raw/Dataset persistence is deferred to the encrypted recording slice.
- P-VS-2 native work is parked until exact Model/License/Runtime and applicable
  Human authorization are recorded.
- Each locale receives independent language, script, G2P, alignment, font,
  license, provider and Human calibration gates.

Final unresolved Critical/High: `0 / 0`.

## Judge decision

Decision: `PASS_FOR_DOCUMENTATION_HOSTING / CONDITIONAL_IMPLEMENTATION`.

P-VS-0 may be committed and hosted as a documentation-only PR. It formally
allocates TASK-046/047/048 and corrects current-state/roadmap drift. It does not
authorize runtime behavior.

After P-VS-0 and the Work Lock Registry are all-green on main, fresh-main
AUTONOMY may start P-VS-1A within its exact body-free Allowed Files while
P-UX-1C continues in its disjoint Lock. P-VS-1A may merge only after P-UX-1C
hosted closure and fresh-main rebase. The successor Voice Studio canonical mock
must be hosted before separately authorized P-VS-1B Shell/TASK-014 integration.
Native Model download/generation, recording, training, private audio storage,
OBS/RX/REAPER mutation, paid/Cloud work, version, Tag, Release and Deploy remain
parked until their explicit gates are satisfied.

## Validation

- package file integrity: `13 / 13 PASS`, mismatches `0`;
- OR Crosswalk rows: `32 / 32`;
- Decision Crosswalk rows: `44 / 44`;
- canonical design imported hash: PASS;
- Windows full regression: `1166 passed, 1 intentional non-Windows skip`;
- Ubuntu WSL2 full regression: `1167 / 1167 PASS`;
- `git diff --check`: PASS;
- runtime/source/schema changes: `0`.
