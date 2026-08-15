# TASK-046 P-VS-1A Current Main Audit / Builder Design / Critic / Judge

Date: 2026-08-15
Branch: `codex/task-046-p-vs-1a-body-free-backend`
Initial allocation main: `5e9d8405b6d39f0e726689e4153de8bb8416bf0d`
Fresh-main rebase: `841cda2e5f4eb4dbc5304d5f57afe49392723825`
Unit: `BODY_FREE_METADATA_FOUNDATION_ONLY`

## Current Main Audit

- GitHub main was `5e9d840` at allocation and advanced through the disjoint
  TASK-047 roadmap-only PR #92 to `841cda2`. Public open PR count was zero at
  both audits. This branch was rebased to `841cda2`; Allowed Files overlap is
  zero.
- `docs/ai-team/work-locks/ACTIVE-WORK-LOCKS.json` records
  `BVP-LOCK-TASK046-PVS1A=ACTIVE` and names this exact branch and Allowed Files.
- P-VS-1A branch development is authorized now. Merge remains conditional on
  TASK-036 P-UX-1C hosted closure, fresh-main rebase, zero overlap, DEV-4
  validation, Critic/Judge acceptance and hosted checks.
- The earlier handoff source snapshot `25e2e04` is historical. Main additionally
  contains PR #91, which activates the disjoint P-VS-1A Lock and is the current
  implementation Source of Truth.
- The existing `owner_narration.py::VoiceProfile` is the canonical narration
  identity. It and the narration planner are read-only dependencies.
- Another developer owns active TASK-036 and TASK-047 worktrees. This unit uses
  a fresh isolated clone and does not inspect, clean, stash, rebase or modify
  those WIP checkouts.

## Authority and exclusions

This unit may add only body-free Voice Profile revision metadata, Consent and
License references, an atomic/CAS project-local store, deterministic
public/private projections, and a non-executing preflight evaluator.

It does not authorize audio or transcript bodies, Dataset contents, speaker
embeddings, credential values, private provider voice IDs, host paths, model or
runtime download/load/probe/inference, TTS, training, recording, OBS, Shell,
Timeline, TASK-036, TASK-044, Cloud/paid execution, external application
mutation, Release or Deploy.

## Builder detailed design

### Domain boundary

`VoiceProfileRevision` is an immutable metadata revision bound to the opaque
`voice_profile_id` and exact `profile_digest` owned by TASK-014. It is deliberately not named
`VoiceProfile`, cannot create a TASK-014 narration object and contains no
narration-planning behavior.

Each revision contains:

- exact `voice_profile_id`, TASK-014 canonical narration profile SHA-256,
  monotonically increasing `revision`, parent digest and its own canonical
  SHA-256;
- a `ConsentReference` with subject reference, scope, allowed usage classes,
  verification/revocation state and exact evidence digest;
- a `LicenseReference` with exact model artifact/model/runtime identity,
  artifact hash, license class, evidence digest and fail-closed admission state;
- a `LocalVoiceCapabilityDescription` with declared languages/capabilities,
  offline-only flag and optional independently produced probe-report digest;
- fixed boundary flags proving that no audio body, Dataset body, embedding,
  transcript, credential, private provider ID or host path is persisted.

Unknown Consent, License or capability proof is represented explicitly and is
never promoted to approval by a model-family label or boolean default.

### Stable successor binding

Downstream P-OBS-1 and later Voice slices may refer to a revision only by the
stable tuple `voice_profile_id + canonical_narration_profile_sha256 + revision
+ voice_profile_revision_sha256`.
The public projection additionally exposes Consent and License digests and
states, but not subject/evidence references. A downstream component must never
silently resolve an old Project to the newest revision.

### Store and recovery

The store is project-local at
`.bai-project/voice-profile-revisions.json`. It accepts only:

1. `create` for revision 1 with no parent; or
2. `append` for exactly the next revision whose parent digest equals the latest
   immutable revision, with the caller's exact previous store SHA-256.

The complete read-check-write cycle is serialized with the existing bounded
cross-process file lock. Writes use `AtomicJsonWriter`, validate the temporary
document before replacement and retain all earlier revisions byte-equivalently
in canonical form. Load verifies the store checksum, every revision checksum,
the exact parent chain, identity stability, boundary flags, UTF-8 JSON type,
size bound and non-symlink paths. A CAS mismatch or damaged history fails
closed and never synthesizes a successful update.

### Projection

The private projection contains only the authorized body-free metadata. The
public projection includes the stable revision binding, state enums,
capabilities and digests. It excludes Consent subject/scope text, evidence IDs,
raw audio, transcripts, embeddings, credentials, private provider IDs and host
paths. Both projections are deterministic.

### Non-executing preflight

`VoiceStudioPreflightService.evaluate` is a pure metadata evaluator. It receives
a revision plus requested language, usage class and capability, and returns a
deterministic report. It has no adapter, callback, process, network, filesystem
probe or dispatch method. Admission requires active verified Consent, requested
usage in scope, approved exact License evidence, approved exact artifact,
offline-only capability metadata, verified probe evidence and matching
language/capability. Any missing/unknown/revoked/inconsistent input is blocked
with stable reason codes. Even `READY` means metadata-ready only and explicitly
does not authorize execution.

## Critic pass 1

Decision: `CHANGES_REQUIRED`.

1. **High — duplicate VoiceProfile risk.** An earlier shape could have become a
   second narration identity. Corrected by making `VoiceProfileRevision` an
   immutable metadata attachment to TASK-014's opaque `voice_profile_id`, with
   no conversion or planner API.
2. **High — mutable-history risk.** A general `save(history)` API could rewrite
   earlier biometric metadata. Corrected to first-create and exact-CAS append,
   exact revision increment, exact parent hash and full-chain validation.
3. **High — unsafe UNKNOWN defaults.** Separate booleans could admit unknown
   Consent or License evidence. Corrected to explicit states and cross-field
   invariants; UNKNOWN and REVOKED/BLOCKED fail closed.
4. **Medium — public metadata leakage.** Subject, scope and evidence references
   could identify private records. Corrected to publish only state and canonical
   digests while retaining full body-free references in the private store.

Unresolved Critical/High after corrections: `0 / 0`.

## Critic pass 2

Decision: `CHANGES_REQUIRED`.

1. **High — preflight could imply runtime authority.** Corrected to a pure
   evaluator with no execution port and an explicit
   `execution_authorized=false` result even when metadata is ready.
2. **High — capability labels could fabricate proof.** Corrected so `VERIFIED`
   requires an exact probe-report digest; family/model names alone remain
   blocked.
3. **High — commercial admission could contradict License class.** Corrected
   with invariants tying commercial approval to `COMMERCIAL_ALLOWED`, exact
   evidence and approved artifact state.
4. **Medium — later OBS reference could drift to latest.** Corrected by exposing
   the exact revision binding and forbidding implicit latest-revision adoption.

Unresolved Critical/High after corrections: `0 / 0`.

## Judge decision

Decision: `PASS_FOR_BOUNDED_IMPLEMENTATION`.

Implementation may proceed only in the hosted Lock's exact Allowed Files and
must preserve every exclusion above. Required validation is schema parity and
validation, deterministic projections, TASK-014 identity coexistence, append
and restart round-trip, stale/missing CAS, tamper/chain/symlink rejection,
failure-injected atomicity, fail-closed preflight, focused tests, Windows and
WSL full regression, `git diff --check`, Allowed Files zero-overlap audit and
post-push hosted checks. Merge remains parked until all external merge
conditions are satisfied.
