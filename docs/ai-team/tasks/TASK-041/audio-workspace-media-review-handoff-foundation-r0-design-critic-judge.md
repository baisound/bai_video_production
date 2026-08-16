# TASK-041 Audio Workspace Media Review / Handoff Foundation R0

- Date: 2026-08-17
- Authority: Owner autonomous roadmap queue / TASK-041 remaining Audio Workspace slice
- Initial base: `main@6ef869098b0bc629deb87d1d6e964c4e3fbfc44d`
- Fresh integrated base: `main@8dddd2b7caadd1daaba87aa4f3bc73a183e9dd73`
- State: `PURE_METADATA_IMPLEMENTED_AND_LOCALLY_VALIDATED`
- Effects: audio read/playback/waveform render/media strip/Asset registration/placement mutation/DAW launch = `false`

## A. Scope and no-duplicate decision

This slice closes the metadata boundary left by the original TASK-041 detailed
design without reopening its hosted foundations.

| Concern | Canonical owner reused | This slice owns |
|---|---|---|
| Audio Workspace registry, placement decision and CAS store | Existing TASK-041 modules | No duplicate |
| TASK-026 placement plan | TASK-026 | Exact hash reference only |
| Asset bytes, revision, rights and promotion | TASK-003 | Body-free source binding/proposal only |
| REAPER session, render, QA and round trip | TASK-035 | Handoff/status binding only |
| Playback, decoding and waveform generation | Future external adapter | Capability and external receipt binding only |
| Human audio/visual review | Owner Human review | Immutable decision metadata |

Existing `audio_workspace.py`, `audio_workspace_store.py`,
`audio_workspace_application.py`, `audio_workspace_placement_binding.py`,
`reaper_audio_finishing.py`, `production_dashboard.py`, Shell/UI, Registry and
shared exports remain unchanged.

## B. Canonical serialized records

1. `AudioMediaReviewPolicyRevision`
2. `AudioMediaSourceBinding`
3. `PlaybackWaveformCapabilityBinding`
4. `AudioMediaReviewIntent`
5. `ExternalAudioReviewReceiptBinding`
6. `DerivedAudioAssetProposal`
7. `AudioMediaReviewDecision`
8. `DawRoundTripStatusBinding`

All records reject unknown properties, use deterministic canonical JSON and a
`sha256:` record digest, and contain no audio/text body, absolute path or
credential. Revisions are append-only: revision 1 has no parent; later
revisions require the exact parent digest.

## C. Review admission

`classify_review_admission` validates exact policy/source/capability/intent
hashes, current observation age, rights, 48 kHz policy, half-open integer sample
range, source duration, requested playback/waveform capability and policy caps.

- `READY_FOR_HUMAN_REVIEW` means metadata preconditions are satisfied.
- `BLOCKED` means an affirmative mismatch, expiry, unsupported capability or
  rights block exists.
- `UNKNOWN` means an unresolved canonical binding, rights state or capability
  prevents a reliable decision.

It never starts playback, waveform rendering, media processing, a DAW, Asset
registration or placement mutation.

## D. External playback/waveform receipt

The pure module cannot issue an authoritative playback/waveform receipt. It
validates an externally supplied `ExternalAudioReviewReceiptBinding` and proves
exact inclusion of the intent, source, capability and half-open sample range.
`COMPLETED` requires authoritative persistence. An unresolved receipt is null
throughout and cannot invent a successful observation. A range mismatch is not
weakened to success.

## E. Independent visual/audio decision and derived proposals

`AudioMediaReviewDecision` stores the Owner Human decision separately for audio
and picture. Therefore visual PASS + audio STRIP and visual FAIL + audio retain
remain representable without an all-or-nothing reject.

`DerivedAudioAssetProposal` is proposal-only. It binds the exact source and
review intent, requires source preservation, and keeps
`derived_bytes_present=false`, `asset_registration_started=false`, and
`media_mutation_started=false`. Actual strip/audio-only creation and TASK-003
registration require separate effects and receipts. Original bytes are never
overwritten by this contract.

## F. REAPER boundary

`DawRoundTripStatusBinding` references the exact TASK-035 manifest. It may show
proposed, externally pending, returned or unknown state. A returned state needs
an exact returned Candidate binding. The module does not launch REAPER, read a
project, render audio, approve a mix, promote an Asset or mutate Resolve.

Owner has allowed later bounded REAPER application operation. That authority is
not converted into an automatic effect by this metadata slice; an operation
must still bind the executable/project/output and preserve source material.

## G. Privacy and projection

Private projection returns the validated body-free record. Public projection
contains only record/type/state/decision/reason summaries and explicit false
privacy flags. Canonical references, Asset hashes, application identity,
receipt refs, sample ranges and private provenance are suppressed.

## H. Allowed files and release metadata

Task-owned implementation files are exactly:

1. this Evidence document;
2. `schemas/audio-workspace-media-review.schema.json`;
3. its byte-exact schema resource mirror;
4. `src/ai_video_production/audio_workspace_media_review.py`;
5. `tests/test_task041_audio_workspace_media_review.py`.

`CHANGELOG.md` is a separate serialized shared-file composition. At the initial
implementation checkpoint PR #157 already owns a CHANGELOG change; therefore
this slice performs no concurrent shared write. It may add one Japanese
`[Unreleased]` bullet only after fresh zero-overlap read-back.

## I. Acceptance matrix

- Eight root records validate through both runtime and Draft 2020-12 schema.
- Public/mirror schema bytes are identical.
- Canonical hash is deterministic; tamper is rejected.
- Unknown/extra/forgeable `execution_authorized` fields are rejected.
- Absolute paths and credential-like references are rejected.
- Unresolved bindings cannot carry canonical truth.
- Rights unknown and capability probe-required remain UNKNOWN.
- Hash/range/rate/staleness drift fail closed.
- External receipt inclusion requires exact intent/source/capability/range.
- Completed receipt without persistence is rejected.
- Visual and audio decisions remain independent.
- Strip/alternate decisions require an exact derived proposal.
- Proposal cannot claim derived bytes, Asset registration or mutation.
- DAW returned state requires returned Candidate; DAW effects remain false.
- Public projection leaks no canonical ref/hash/path/audio body.
- Static effect surface contains only `false`.

## J. Validation Evidence

- Focused WSL2: `17 passed`.
- Schema mirror byte equality: required and covered.
- Windows focused: `17 passed`; full: `1669 passed, 1 skipped`, plus one
  known unrelated TASK-047 installer acceptance failure (`exit=4`) in the
  managed Windows environment. The initial default-temp run was separately
  invalidated by a pre-existing pytest temp-root access denial; the dedicated
  workspace basetemp removed those 542 setup errors.
- WSL2 full regression after fresh-main integration: `1694 passed, 1 skipped`.
- Hosted checks: pending Draft PR.

## K. Critic pass 1

### Builder

Finding: the remaining TASK-041 design could be misread as permission to add a
second playback engine, media writer, Asset publisher or placement service.

Correction: the new module only compiles/validates immutable metadata and an
external-receipt inclusion proof. Existing implementations are read-only
dependencies; all effect flags are fixed false.

### Security

Finding: source/application/receipt coordinates could expose paths, credentials
or voice-linkable/private hashes through public UI.

Correction: identifier validation rejects absolute/traversal/credential-like
values, body/path flags are false, and public projection removes canonical and
receipt coordinates.

### Compatibility

Finding: representing strip output as an existing Asset or a REAPER return as a
successful render would forge downstream truth.

Correction: derived output is `Proposal` only; external audition and TASK-035
round-trip status require structured canonical bindings and exact inclusion.

## L. Critic pass 2

- Existing TASK-041/TASK-026/TASK-035 ownership duplication: 0.
- Audio/path/credential/public leakage: 0.
- Effect or Human authority escalation: 0.
- Unknown-to-PASS conversion: 0.
- Original-byte overwrite path: 0.
- Schema/runtime root-name drift: 0.
- Unresolved Critical/High/Medium: `0 / 0 / 0`.

## M. Judge

- `DOMAIN_READINESS=PASS`
- `PURE_METADATA_IMPLEMENTATION=PASS`
- `PLAYBACK/WAVEFORM/MEDIA/ASSET/PLACEMENT/DAW_EFFECT=BLOCKED_BY_SEPARATE_GATE`
- `TASK041_EXISTING_FOUNDATIONS_REIMPLEMENTED=NO`
- `RELEASE/DEPLOY/PRODUCTION=NOT_AUTHORIZED_BY_THIS_UNIT`
- Residual Critical/High/Medium: `0 / 0 / 0`
