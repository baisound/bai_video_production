# TASK-046 P-VS-1A Implementation / Validation / Critic Evidence

Date: 2026-08-15
Branch: `codex/task-046-p-vs-1a-body-free-backend`
Fresh-main base: `841cda2e5f4eb4dbc5304d5f57afe49392723825`
Lock: `BVP-LOCK-TASK046-PVS1A=ACTIVE`

## Result

P-VS-1A body-free Voice Profile metadata foundation is complete for a branch
checkpoint. It adds no second `VoiceProfile` class and no narration planner.
Every metadata revision binds both the existing TASK-014
`voice_profile_id` and its exact canonical `profile_digest`.

Implemented:

- immutable `VoiceProfileRevision`, Consent, exact Model/License and declared
  local capability metadata with canonical nested and revision SHA-256;
- explicit UNKNOWN/ACTIVE/REVOKED and catalog/evaluation/approved/blocked
  states with cross-field fail-closed invariants;
- deterministic body-free private projection and redacted public projection;
- project-local `.bai-project/voice-profile-revisions.json` first-create and
  exact-CAS append-only history;
- cross-process serialized read-check-replace, atomic temporary validation,
  contiguous revision and exact-parent enforcement, restart/tamper/symlink and
  injected-failure handling;
- a pure metadata preflight that never probes, loads, downloads or invokes a
  Runtime/Model and always returns `execution_authorized=false`.

## Boundary proof

The implementation files contain no process, socket, HTTP, Provider, model
load, download, recording, audio-body, OBS, Shell or Timeline integration. The
only model-load marker is the explicit report field `model_load_started=false`.
No credential value, private provider voice ID, host path, raw audio,
transcript, Dataset body or speaker embedding is accepted by the domain model
or persisted by the store.

P-VS-1A does not claim the broader Code/Model/Weight/Dataset/Output License
chain complete. Its `LicenseReference` is deliberately the exact Model Artifact
admission reference for this bounded foundation. Later License-lineage slices
must add separate typed evidence without weakening or overloading this record.

## Implementation Critic pass 1

Decision: `CHANGES_REQUIRED`.

1. Enum-typed states could receive raw strings through direct construction and
   bypass intended invariants. Explicit runtime type checks were added.
2. Append against a missing store was reported as a generic invalid file.
   Exact `ERR_VOICE_PROFILE_STORE_PREVIOUS_MISSING` handling was added without
   creating a snapshot.
3. A known but `RESTRICTED` License could pass a non-commercial request. It now
   emits `MODEL_LICENSE_RESTRICTED` and remains blocked.

Unresolved Critical/High after correction: `0 / 0`.

## Implementation Critic pass 2

Decision: `CHANGES_REQUIRED`.

1. **High — canonical narration binding was ID-only.** TASK-014 permits an
   exact `profile_digest`, so a repeated ID could otherwise bind to different
   private narration state. Every P-VS-1A revision, public projection and
   preflight report now requires the exact TASK-014 canonical narration profile
   SHA-256.
2. **Medium — broader License lineage could be overclaimed.** Evidence and API
   names now describe an exact Model Artifact License reference only; later
   Code/Weight/Dataset/Output evidence remains separate and unimplemented.

Unresolved Critical/High after correction: `0 / 0`.

## Validation

All results below are after the domain correction. Full regressions are after
the fresh-main rebase to `841cda2`.

- focused TASK-046 + TASK-014: `20 passed`;
- Windows full regression: `1181 passed, 1 intentional non-Windows skip` in
  `64.46s`;
- Ubuntu WSL2 full regression: `1182 passed` in `54.46s`;
- schema canonical/package mirror: exact byte parity;
- Python `compileall`: PASS;
- incoming main `5e9d840..841cda2` versus P-VS-1A Allowed Files: overlap `0`;
- public open PR count at final pre-checkpoint audit: `0`;
- audio/model/OBS/Shell/Timeline implementation: `0` files;
- shared Integration files, version, Tag, Release and Deploy changes: `0`.

## Judge

Decision: `PASS_FOR_BRANCH_CHECKPOINT / MERGE_PARKED`.

The body-free unit is ready to commit, push and host as a draft checkpoint.
Hosted checks must pass. Main merge remains parked because
`BVP-LOCK-TASK036-PUX1C` is still `ACTIVE`; the Lock requires its hosted
closure before P-VS-1A merge. No Owner acceptance, native operation, paid
Provider, Credential, private audio, recording, OBS mutation or Release gate is
consumed by this checkpoint.

## Current State / Next Action / Autonomous Queue

- Current State: implementation and local DEV-4 validation PASS on fresh main.
- Next Action: exact-file stage, diff audit, Japanese checkpoint commit, push,
  draft PR and hosted-check observation.
- Parked dependency: merge until TASK-036 P-UX-1C hosted closure and another
  fresh-main/overlap audit.
- Human Gates: all recording, private body, native Model/runtime execution,
  paid/Cloud/Credential, external app mutation, Human acceptance and Release
  gates remain untouched.
- Autonomous Queue after hosted checkpoint: no additional authorized P-VS-1A
  implementation; wait for dependency closure instead of entering P-VS-1B,
  P-VS-2, P-OBS-0/1, recording or training.

## Context Cost / Resume Handoff

The unit loaded only current Governance/Lock/Task records, TASK-014 identity,
atomic/serialization/store dependencies, relevant Voice Studio design sections
and this unit's files. A resumed session needs this Evidence, the two P-VS-1A
documents, the current main Lock Registry and the hosted PR/check state; a full
Repository reload is unnecessary.
