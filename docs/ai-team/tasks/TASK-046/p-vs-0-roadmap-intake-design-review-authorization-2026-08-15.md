# TASK-046 P-VS-0 Roadmap Intake, Design Review and Authorization

Date: 2026-08-15
Exact base main: `244e86aaa0ea65bdba2ca35176c422bcfc30d65f`
Branch: `codex/task-046-voice-studio-roadmap-intake`
Unit: `DESIGN_AND_GOVERNANCE_ONLY`

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
3. TASK-046 P-VS-1 non-executing Voice foundation.
4. exact local voice Model/Runtime/License capability decision.
5. P-VS-2 Japanese, owner-only, Local/free 60–90 second vertical slice.
6. P-VS-3 recording/Dataset and P-VS-4 fine-tuning.
7. TASK-048 quality calibration.
8. TASK-047 OBS capture.
9. TASK-035 RX 12/REAPER finishing.
10. Managed Runtime, broader Local Creative AI and staged locale gates.

This moves the vertical slice ahead of breadth while preserving the existing
mock-authority route. It does not claim the native vertical slice complete.

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

## Builder design — first implementation unit P-VS-1

After P-VS-0 and P-UX-1C hosted closure, fresh main may implement only:

- immutable private `VoiceProfile` revision and consent/license status;
- project-local atomic/CAS store with no raw voice body in public projections;
- local engine capability interface and non-executing preflight;
- deterministic public/private projection and secret/path redaction;
- failure/restart/tamper tests using synthetic metadata only.

Tentative exact implementation files:

- `src/ai_video_production/voice_profile.py`
- `src/ai_video_production/voice_profile_store.py`
- `src/ai_video_production/voice_studio_application.py`
- `src/ai_video_production/__init__.py`
- `schemas/voice-profile.schema.json`
- `src/ai_video_production/schema_resources/voice-profile.schema.json`
- focused `tests/test_task046_*.py`
- the minimal Product-owned documentation/Evidence/CHANGELOG files needed for
  truthful synchronization.

P-VS-1 excludes recording, audio body import, engine/model download, TTS,
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

1. **High — P-VS-1 still risked implicit execution.** A local adapter interface
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

- P-VS-1 is explicitly non-executing and body-free; exact model download and
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

After P-VS-0 is all-green on main, TASK-036 P-UX-1C is hosted-closed and the
successor Voice Studio canonical mock is hosted, fresh-main AUTONOMY may start
P-VS-1 within its exact body-free Allowed Files.
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
