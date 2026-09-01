# TASK-073 — Owner Voice Local WAV Product Vertical Slice

- Status: `D4_R4_UX_DESIGN_ACCEPTED / TASK073_SOURCE_HOLD / TASK036_P0V_START0 / SUCCESSOR_MOCK_OWNER_CHECK_PENDING`
- Priority: `P0-V / COEQUAL OWNER OUTCOME`
- Governance: `DEV-4 FOUNDATION CRITICAL`
- Allocation date: `2026-09-01`
- Allocation authority: Owner-approved design/development reorganization
- Design owner: `Design A / Product Experience & AI`
- Builder: `Outcome V / Voice WAV primary (Development5)`
- Platform review: `Design B / Platform Trust & Delivery`
- Independent review: `Montage Critic / Judge`
- D1 design base: `origin/main@c27c24d6cb5f936e0549b743084bb9a9eaceb545`
- D2 reconciliation base: `origin/main@70ba9e369887d3d7ded59e7197d20d133b2b4d38`
- D3 correction base: `origin/main@70ba9e369887d3d7ded59e7197d20d133b2b4d38`
- D4 closure base: `origin/main@70ba9e369887d3d7ded59e7197d20d133b2b4d38`
- D4-R4 correction parent: PR `#482` merge
  `efdcd77729732e3c50abb9e4a7e89ae2b7b37aa0`

## Objective

Close one Product-visible, local-first path from the Owner's consented voice
material to a technically verified and Human-accepted canonical-format WAV:

```text
BAI Video Production.exe
→ Voice Studio
→ local/free voice-model selection
→ Owner reference / Dataset and training preparation
→ local inference
→ technical WAV QA
→ Owner listening decision
→ accepted private staging WAV
```

The target format is `48 kHz / 24-bit integer PCM / mono`.  "Optimal" means
the best accepted candidate under explicit technical metrics, current model and
runtime Evidence, and the Owner's listening decision.  It is not an absolute
or self-asserted quality claim.

## Responsibility boundary

TASK-073 owns only a non-authoritative Product composition/read model,
request-to-receipt correlation, public-safe UI projection and packaged
synthetic end-to-end contract.  It does not own a canonical operation state
machine and does not mint, persist, transition, consume or repair authority.
Every displayed state is derived from freshly verified receipts created by the
existing canonical owners and the bounded producer Tasks allocated by D2.

It does not create a second source of truth for any of the following:

- narration plan/render/publication (`TASK-014`);
- VoiceProfile, Consent, Dataset, TrainingInput or ModelCandidate (`TASK-046`);
- calibration and acoustic quality (`TASK-048`);
- model inventory (`TASK-013`);
- compute preference/admission (`TASK-066`);
- Asset adoption (`TASK-003`);
- durable execution/recovery (`TASK-020` / `TASK-043`);
- Shell/startup/single-instance (`TASK-036`);
- Timeline or Export Queue (`TASK-044`).

Training preparation is in scope.  Training dispatch, ModelCandidate approval,
Asset adoption and Export remain separate effect-specific Human Gates.

TASK-073 performs no filesystem open/write/replace/delete, model or child
process execution, capability burn, playback, technical QA, job recovery or
WAV publication.  It requests those effects through versioned producer ports,
correlates their opaque receipts and projects only public-safe state.

## Design files allowed now

1. `docs/ai-team/tasks/TASK-073/task.md`
2. `docs/ai-team/tasks/TASK-073/p0v-owner-voice-local-wav-complete-design.md`
   (`D1`, immutable failed history)
3. `docs/ai-team/tasks/TASK-073/p0v-owner-voice-local-wav-complete-design-d2.md`
   (`D2`, immutable failed history)
4. `docs/ai-team/tasks/TASK-073/p0v-owner-voice-local-wav-complete-design-d3.md`
   (`D3`, immutable failed history)
5. `docs/ai-team/tasks/TASK-073/p0v-owner-voice-local-wav-complete-design-d4.md`
   (`D4 R0`, immutable failed history)
6. `docs/ai-team/tasks/TASK-073/p0v-owner-voice-local-wav-complete-design-d4-r1-closure.md`
   (`D4 R1`, immutable failed history)
7. `docs/ai-team/tasks/TASK-073/p0v-owner-voice-local-wav-complete-design-d4-r2-closure.md`
   (`D4 R2`, immutable failed history)
8. `docs/ai-team/tasks/TASK-073/p0v-owner-voice-local-wav-complete-design-d4-r3-closure.md`
   (`D4 R3`, immutable accepted mechanical history; mock UX superseded by R4)
9. `docs/ai-team/tasks/TASK-073/p0v-owner-voice-local-wav-complete-design-d4-r4-ux-closure.md`
10. `docs/ai-team/tasks/TASK-073/design-review-receipt.md`
11. `docs/ai-team/tasks/TASK-073/p0v-voice-studio-successor-mock.html`
12. `docs/ai-team/tasks/TASK-073/p0v-voice-studio-successor-mock-manifest.md`

No Product source, schema, test, packaging, shared-state or CHANGELOG file may
be changed until this complete design receives independent `C/H = 0` and Judge
`PASS`.

## Candidate implementation files after design PASS

### TASK-073-owned new files

1. `schemas/task073-owner-voice-local-wav-composition.schema.json`
2. `src/ai_video_production/schema_resources/task073-owner-voice-local-wav-composition.schema.json`
3. `src/ai_video_production/task073_owner_voice_local_wav_composition.py`
4. `src/ai_video_production/task073_owner_voice_local_wav_application.py`
5. `src/ai_video_production/task073_owner_voice_local_wav_projection.py`
6. `tests/test_task073_owner_voice_local_wav_composition.py`
7. `tests/test_task073_owner_voice_local_wav_application.py`
8. `tests/test_task073_owner_voice_local_wav_projection.py`
9. `tests/test_task073_owner_voice_local_wav_product_integration.py`

### TASK-036 consumer handoff, outside TASK-073 Allowed Files

TASK-036 is the sole integration owner for Product Shell, UI and packaged-entry
source.  TASK-073 publishes a versioned composition fixture and completion
receipt to Outcome E; TASK-073 never edits TASK-036 source or tests.  The
successor Voice Studio mock must first receive an explicit Owner check.
GF-B/P0-E producer implementation PRs must be merged to canonical main, their
branches/locks released, and a fresh-main overlap/lock audit must admit the
separate TASK-036 amendment.  An accepted design head or open PR is
insufficient.
If implementation discovery proves an additional existing file is necessary,
Design A must issue a new bounded Allowed-Files amendment before mutation.

## Must not modify

- existing TASK-014, TASK-046, TASK-048, TASK-013 or TASK-066 source, schemas
  and tests;
- `src/ai_video_production/atomic.py`;
- existing installer scripts, PyInstaller specs and batch files;
- canonical Asset, Dataset, Model, Job, Timeline, Export or credential stores;
- shared `current-state`, `task-index`, roadmap or `CHANGELOG.md` without the
  sole-Builder/lock workflow;
- BAI Development OS or Canonical SKILL repositories.

PR #470 and PR #476 are preserved dependencies.  Raw cherry-pick, rebase,
force-push, branch overwrite and unreviewed code copying are prohibited.

## Dependency gates

The design is not dependency-gated.  Implementation is split so only the
effect that needs a producer receipt is parked.

1. TASK-068 secure authority I/O and TASK-076 secure Durable Product Job
   amendment completion receipts.
2. TASK-070 is consumed only through `TASK-063 INSTALLATION_READBACK_V2`, then
   TASK-072 installed profile binding, then TASK-036 P0-E
   `INSTALLED_STARTUP_CONTEXT_V1`; TASK-073 never reads TASK-070 private state.
3. TASK-074 Voice authority/selection/private-reference completion, including
   TASK-071 action and TASK-072 consumer-profile amendments.
4. TASK-075 local Voice execution/listening broker completion, including
   TASK-014/TASK-048/TASK-066/TASK-072 bounded owner amendments.
5. PR #470 accepted and merged for the TASK-014 zero-shot callable contract.
6. PR #476 accepted and merged for the TASK-046 Quick Clone lifecycle/readback.
7. For the separate `P0V_OWNER_OUTCOME_VERIFIED` result only: TASK-036 P0-E
   startup/single-instance/packaged composition is accepted and merged, and
   the successor mock has an exact Owner check.

## Completion

`TASK073_IMPLEMENTATION_PR_READY` requires the accepted D4 plus D4-R1,
D4-R2, D4-R3 and D4-R4 closures,
TASK-073-owned implementation, focused and negative tests, required
regressions, application-level synthetic composition QA, independent
Critic/Tester/Judge, scope review, commit, push and one coherent Draft PR.  It
does not require or authorize a TASK-036 change or packaged synthetic E2E.

`TASK073_IMPLEMENTATION_COMPLETE` is stronger: the exact accepted
`TASK073_IMPLEMENTATION_PR_READY` head must be merged to canonical main,
required hosted checks must succeed and a fresh-main readback must match the
accepted implementation and receipt identities.

`TASK036_P0V_INTEGRATION_COMPLETE` is a separate Outcome E result.  It
requires canonical D4/D4-R1/D4-R2/D4-R3/D4-R4/mock/manifest hashes and their exact design
bundle digest, successful hosted checks,
fresh-main readback, a separate verified `TASK073_OWNER_MOCK_CHECK_RECEIPT_V1`
with `OWNER_CHECK_PASS`, a separately authorized
TASK-036 P0-V Atomic Unit/Allowed Files/lock and installed packaged synthetic
E2E.

`P0V_OWNER_OUTCOME_VERIFIED` is a separate higher result.  It requires a real
Owner-authorized E3-E5 run through the separately integrated packaged Product
with exact private reference, local inference, technical QA, listening
decision and accepted WAV readback all `PASS`.
Synthetic PASS or `NOT_CONFIRMED` can never produce this result.

Real Owner-audio native execution is recorded separately as `PASS`, `FAIL` or
`NOT_CONFIRMED`.  Release, Deploy, Production Activation, Cloud/paid execution,
training dispatch, Asset adoption and Export are not authorized by this Task.
