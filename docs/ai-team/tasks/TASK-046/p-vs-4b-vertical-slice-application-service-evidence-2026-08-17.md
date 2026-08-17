# TASK-046 / P-VS-4B Vertical Slice Application Service — Evidence

Date: 2026-08-17
Base: `main@868548ebec65ebec565b62dd45bc45da99db2fb1`
Branch: `codex/task-046-p-vs-4b-vertical-slice-service`

## Outcome

This unit implements the first pure application-service layer for the Owner's
priority path: reviewed OBS recordings → Dataset/Training snapshot → trained
and approved Model candidate → ordered style Cue renders → one natural 48 kHz
Master WAV candidate.

It composes existing canonical coordinates only. It does not read a WAV, crawl
a directory, create/adopt a Dataset, create/dispatch a Job, load/train/infer a
model, reserve a GPU, render or assemble audio, write/register an Asset, issue
Owner approval, publish, release or deploy.

## Canonical types

1. `CanonicalSourceBinding`
2. `StyleCueRevision`
3. `MasterAssemblyPolicyBinding`
4. `MasterWavCandidateRevision`
5. `VerticalSliceWorkflowRevision`
6. `ExternalOperationRequest`

`CanonicalSourceBinding` references TASK-047/P-QC/TASK-003/P-VS-3B/P-VS-4A/
TASK-014 truth. It never becomes a duplicate Dataset, Model, Consent, Job or
Asset owner.

## Invariants

- External operations are immutable `PROPOSAL_ONLY` records with
  `dispatch_started=false`; a structured authorization-binding digest is
  required but is not issued by this module.
- Cue revisions bind exact script range, style direction, ModelCandidate,
  VoiceProfile and TASK-014 render-admission hashes. An unrendered Cue cannot
  claim a receipt or artifact.
- A Master contains at least two unique ordered Cue hashes and exact single
  ModelCandidate/VoiceProfile lineage.
- Master format policy is exactly 48 kHz, 24-bit integer PCM, mono. Pause,
  loudness, boundary and identity policies are separately bound and remain
  UNKNOWN when their canonical policy is unavailable.
- Owner Master acceptance requires a bound external assembly receipt/artifact
  and PASS for format, boundary, loudness, identity continuity and style.
- Master acceptance is not Asset adoption, VoiceProfile binding, publication,
  Release or Deploy.
- Public beginner projection hides source coordinates and shows UNKNOWN as an
  explicit state; it never converts missing Evidence to zero, 95% or PASS.

## Acceptance negatives

- arbitrary folder/absolute/private path as source;
- unresolved source inventing a canonical ref/hash;
- duplicate source owners or Cue hashes;
- Cue body persistence or unrendered artifact claim;
- 44.1 kHz/non-mono/non-24-bit Master policy;
- one-Cue or duplicate-Cue Master;
- UNKNOWN boundary/style/identity accepted as natural Master;
- forged dispatch boolean or unknown fields;
- broken workflow revision/CAS parent;
- public leakage of canonical source coordinates.

## Validation

- focused tests: `19 passed`;
- schema mirror: byte exact, SHA-256
  `3a32ff845177405d4f3385b2b2985287d754480e2f575dc9e60d56a1102f0467`;
- Windows full regression excluding the unrelated TASK-047 installer effect:
  `1813 passed, 1 skipped, 1 deselected` in `80.33s`;
- WSL2 full regression: `1814 passed, 1 skipped` in `71.02s`;
- Python compile and no-effect static surface: PASS.

## Critic pass 1

- Builder: ensure Cue and workflow revision parents are append-only exact CAS.
- Security: reject absolute/private identities and audio-body persistence.
- Compatibility: preserve P-VS-3B/P-VS-4A/TASK-014 ownership and avoid
  importing their runtime effects.

Corrections are represented by strict validators and negative tests.

## Critic pass 2 / Judge

- Builder: six canonical records, CAS lineage, Cue ordering and exact Master
  acceptance prerequisites PASS.
- Security/privacy: body/path/credential rejection, proposal-only external
  operations and public coordinate suppression PASS.
- Compatibility: canonical source references preserve P-VS-3B/P-VS-4A/
  TASK-014 ownership and modify none of those modules PASS.
- Residual Critical/High/Medium: `0 / 0 / 0`.
- Dataset/Training/Model/Audio/Asset/Production effect: `BLOCKED`.
