# TASK-047 P-OBS Priority Dependency — Audit, Design, Critic and Judge

Date: 2026-08-15
Status: `JUDGE_PASS / VALIDATION_PASS / READY_FOR_DOCS_ONLY_HOSTING / IMPLEMENTATION_NOT_AUTHORIZED`
Governance: `DEV-4 FOUNDATION CRITICAL`
Audit base main: `5e9d8405b6d39f0e726689e4153de8bb8416bf0d`

## Owner decision

Production training-material recording begins only after the minimum OBS Plugin
capture path is hosted and proven. TASK-047 is therefore split without stopping
the current disjoint implementation units:

- `P-OBS-0`: exact installed-target and official development-source
  Capability/SDK/ABI/License/Build design/probe;
- `P-OBS-1`: minimum recoverable selected-input Capture MVP and the P0
  technical dependency for P-VS-3 production recording/P-VS-4 fine-tuning;
- `P-OBS-2`: later continuous meeting/live, multiple Source and advanced
  proposal breadth.

TASK-036 P-UX-1C and TASK-046 P-VS-1A remain active under their existing
disjoint File Locks. This unit changes Governance documents only and does not
change either implementation checkout.

## Current OS and repository audit

- Remote `main` and the fresh standalone checkout matched exact
  `5e9d8405b6d39f0e726689e4153de8bb8416bf0d` before this unit began.
- PR #91 Lock/Roadmap hosting was merged with `9 / 9` hosted checks and
  post-merge CI/Security PASS.
- The protected TASK-036 P-UX-1C WIP remained at its recorded branch/HEAD and
  matched all `21 / 21` handoff hashes after PR #91.
- TASK-046 P-VS-1A remained a separate reserved Lock and no P-VS-1A
  implementation was started by this unit.
- Existing Ver.1.2 Voice Studio/OBS design identifies the target installation
  root `E:\SteamLibrary\steamapps\common\OBS Studio\bin`, the baseline
  executable `bin\64bit\obs64.exe`, a control-plane WebSocket path, local PCM
  IPC and an OBS real-time callback that must remain bounded.
- No E-drive inspection, OBS launch/configuration, Plugin load/install, capture,
  audio persistence, Model operation, Dataset adoption or training was run.

## DEV Profile and authority

`DEV-4 FOUNDATION CRITICAL` applies because this change controls production
recording, private immutable audio, recovery, consent, licensing and a future
native Plugin boundary. Owner authority grants roadmap/design synchronization,
Critic review and Judge only. It does not grant P-OBS-0 host Probe execution or
P-OBS-1 implementation.

## Exact docs-only Allowed Files

The Integration Lock in `ACTIVE-WORK-LOCKS.json` lists the exact 19 files for
this unit. Changes outside that set are prohibited. In particular, no `src/`,
`tests/`, `schemas/`, `.github/`, build, package, Evidence body or existing WIP
file is writable in this unit.

## Builder design

### P-OBS-0

P-OBS-0 keeps two Evidence identities separate:

1. installed target: executable/module inventory, hashes, version and
   architecture at the exact Owner-provided root;
2. official development source: OBS SDK/Plugin Template source reference,
   commit/version, headers, documentation and license identity obtained only
   through a separately authorized read-only/local-source route.

The installed `bin` tree never proves SDK/header identity. Synthetic ABI/load,
callback, IPC and reproducible-build contracts may be designed without Plugin
load, OBS mutation or capture. Exact Allowed Files, operations and any egress
must be separately authorized before the Probe runs.

### P-OBS-1

Before implementation, hosted contracts must bind:

- existing `owner_narration.VoiceProfile` canonical identity;
- P-VS-1A `VoiceProfileRevision` reference identity;
- TASK-046-owned `VoiceRecordingSession`, segment, Dataset-candidate, review
  and adoption boundary;
- TASK-043-owned durable job/checkpoint/crash-restart boundary.

The Plugin real-time callback copies only bounded native frames and minimum
metadata to a non-blocking ring/IPC boundary. It does not resample, convert bit
depth, analyze, encrypt or write files. A bounded non-real-time worker validates
and converts to canonical 48 kHz/24-bit/mono immutable staging while recording
exact source-frame-to-canonical-sample lineage, missing samples, overrun/drop,
device/build identity and recovery state.

P-OBS-1 owns capture/session transport and raw staging Evidence. TASK-046 owns
Dataset storage, Human review/adoption and VoiceProfile revision truth.
Incomplete/UNKNOWN segments cannot be promoted. Capture never automatically
adopts a Dataset candidate and adoption never automatically starts training.

### P-VS-3 production recording Gate

All five conditions are conjunctive:

1. P-OBS-1 hosted completion;
2. P-OBS-0 exact-path Probe PASS on the supported target;
3. explicit recording Consent for the selected Owner input and purpose;
4. verified encrypted immutable private staging/storage and recovery;
5. explicit Owner GO for the bounded recording Session.

P-VS-2 remains a zero-shot local/free vertical slice and does not authorize or
require new production training-material recording. P-OBS-2 is not required for
the first production recording Gate. Q25 Stable Audio remains independent.

## Critic pass 1

Result before correction: `3 HIGH / 0 CRITICAL`.

1. **HIGH — installed OBS and SDK identity were conflated.** The first draft
   could be read as expecting official SDK headers inside `bin`.
   **Correction:** installed-target Evidence and official-development-source
   Evidence are now separate throughout Task, Architecture, Acceptance,
   Crosswalk, Probe Plan, Roadmap and Registry.
2. **HIGH — P-OBS-1 contract ownership was incomplete.** Starting Plugin work
   without hosted VoiceProfile/Revision, recording session/segment/Dataset and
   recovery bindings could create duplicate Sources of Truth.
   **Correction:** the four hosted contract prerequisites and ownership split
   are explicit.
3. **HIGH — canonical audio conversion risked real-time callback work.**
   **Correction:** callback behavior is copy-only/non-blocking; canonical
   conversion, encryption, analysis and persistence are non-real-time with
   exact sample lineage.

Post-correction unresolved Critical/High: `0 / 0`.

## Critic pass 2

Result before correction: `2 MEDIUM / 0 HIGH / 0 CRITICAL`.

1. **MEDIUM — upper-level summaries still used compressed
   “exact-path/SDK” wording.** A future context-limited AI could reintroduce the
   installed-tree/SDK conflation.
   **Correction:** Project, Current State, Task Index, Architecture, P-VS-0 and
   Roadmap summaries now retain the two-source distinction.
2. **MEDIUM — the current Integration Lock looked released before hosting.**
   **Correction:** it is explicitly active until exact main hosting and
   post-merge checks, then released.

The second pass also verified that the five production-recording conditions are
conjunctive, P-OBS-1 never owns Dataset adoption, P-OBS-2 is later, Q25 is
independent, and the two active implementation Locks remain unchanged.

Post-correction unresolved Critical/High/Medium: `0 / 0 / 0`.

## Judge

Decision: `PASS_FOR_DOCS_ONLY_HOSTING_AFTER_VALIDATION`.

Rationale:

- Owner priority is represented without interrupting P-UX-1C or P-VS-1A;
- dependencies and Task ownership are explicit;
- production recording is blocked by all required Human/security/native Gates;
- P-OBS-0/P-OBS-1 implementation and host mutation are not inferred;
- automatic Dataset adoption and automatic training remain prohibited;
- the change is bounded to the exact docs-only Integration Lock.

This Judge decision does not authorize OBS inspection, Plugin implementation,
recording, private audio storage, Dataset adoption, training, external Provider,
version, Tag, Release or Deploy.

## Validation Evidence

- exact changed/Allowed Files: `19 / 19 PASS`;
- TASK-036 P-UX-1C vs TASK-046 P-VS-1A exact-path overlap: `0 PASS`;
- Lock Registry UTF-8 JSON parse: `PASS`;
- `git diff --check`: `PASS`;
- Windows Python 3.12 compileall: `PASS`;
- Windows full regression: `1166 passed / 1 expected non-Windows skip`;
- Ubuntu WSL2 compileall: `PASS`;
- Ubuntu WSL2 full regression: `1167 / 1167 PASS`;
- unresolved Critic Critical/High/Medium: `0 / 0 / 0`.

Hosted PR checks, exact main merge, post-merge CI/Security and post-hosting
TASK-036 WIP hash verification remain required before this docs-only unit is
closed. Until exact hosting completes, the Integration Lock remains active.
