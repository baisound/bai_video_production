# TASK-014 Local Primary Narration Render Admission R0

Date: 2026-08-17

Authority: `OWNER-AUTH-20260817-DEVELOPER2-EXCLUSIVE-ROADMAP-QUEUE-AUTONOMY-01`

Base: `origin/main@8ce6fd4bb178734260f476386cf44548f8354c72`

The first local composition was based on `349a5902...`. Main then added the
TASK-009 CHANGELOG bullet at the same insertion point. A merge-tree preflight
predicted a CHANGELOG conflict, so no merge or manual conflict resolution was
started. The verified exact-five implementation was byte-copied to this fresh
main worktree; only this Evidence base line and the fresh one-line CHANGELOG
composition differ.

## 1. Allocation and scope

The hosted `LocalPrimaryNarrationPreflight` remains unchanged. This unit adds
the next body-free admission boundary between an approved Local Primary
preflight and an external renderer. It does not implement synthesis.

Exact implementation ownership:

1. `docs/ai-team/tasks/TASK-014/local-primary-narration-render-admission-r0-design-critic-judge.md`
2. `schemas/local-primary-narration-render-admission.schema.json`
3. `src/ai_video_production/schema_resources/local-primary-narration-render-admission.schema.json`
4. `src/ai_video_production/owner_narration_local_render_admission.py`
5. `tests/test_task014_local_primary_narration_render_admission.py`

Release metadata is a separately serialized one-line `CHANGELOG.md` update.
No Registry, roadmap, workflow, shared package export or existing TASK-014
implementation is changed.

## 2. Source-of-truth boundaries

| Truth | Canonical owner | This unit |
|---|---|---|
| approved text and immutable text digest | TASK-006/TASK-014 source revision | exact ID/hash reference only |
| VoiceProfileRevision and current Consent | TASK-046/P-VS-1A | exact ID/hash reference only |
| Local Primary route preflight | hosted TASK-014 I1 | exact preflight decision/hash |
| CPU/RAM/VRAM/disk/process admission | TASK-020 | exact expiring gate binding |
| durable Job identity/idempotency | TASK-043 | exact registered Job binding |
| encrypted staging/recovery/retention/quota | storage owner/TASK-043 | exact private destination policy binding |
| Human execution decision | Owner Human Gate | one-shot exact authorization Evidence binding |
| model load, render, WAV bytes and alignment | future external adapter | not performed or claimed |
| Asset publication and placement | TASK-003/TASK-026/TASK-041 | separate later effects |

The record cannot turn a preflight, resource fact, registered Job or Owner
authorization into execution. Its strongest result is
`READY_FOR_EXTERNAL_DISPATCH_GATE`.

## 3. Contract

`LocalPrimaryNarrationRenderAdmission` is immutable and append-only by
`revision` plus `parent_revision_sha256`. It binds:

- exact `ZERO_SHOT_LOCAL` or `FINE_TUNED_LOCAL` route;
- exact `PREVIEW` or `FULL_RENDER` usage;
- body-free script and VoiceProfileRevision coordinates;
- `LocalPrimaryPreflightBinding`;
- fresh `ResourceAdmissionBinding` scoped to `LOCAL_NARRATION_RENDER`;
- `DurableNarrationJobBinding` in `REGISTERED`, never a reused queued/running Job;
- `OutputStagingDestinationBinding` for private staged 48 kHz mono PCM WAV;
- structured, expiring, one-shot `ExecutionAuthorizationBinding`.

All bindings use
`CANONICAL_REF_NOT_PROVIDED | BOUND_VERIFIED | MISMATCH | UNKNOWN` with strict
state-dependent nullability. Unresolved states cannot carry invented IDs,
hashes, decisions or Evidence.

Classification is deterministic:

- unresolved or unobservable binding -> `UNKNOWN`;
- mismatch, stale/expired Evidence, denied resource, non-registered Job or
  wrong route/usage/text/destination/scope -> `BLOCKED`;
- all exact current bindings -> `READY_FOR_EXTERNAL_DISPATCH_GATE`.

Every effect flag is fixed to false: `execution_started`, `job_dispatched`,
`model_loaded`, `gpu_reserved`, `audio_rendered` and `asset_published`.

## 4. Privacy, security and failure behavior

- No text/audio body, credential value, absolute path or private voice ID is
  accepted.
- Public projection exposes route, intended usage, decision and reason codes,
  but no project/script/profile/job/destination/Evidence identity or digest.
- Strict key sets reject raw `execution_authorized` booleans and authority
  smuggling.
- Canonical JSON and SHA-256 cover the full private metadata record excluding
  only its own digest field.
- Parser recomputes classification and digest; caller-supplied PASS or
  modified content is rejected.
- Preview authorization cannot be reused for full render, and zero-shot
  authorization cannot be reused for fine-tuned rendering.
- Expired resource or authorization receipts never become PASS.

## 5. Acceptance inventory

- positive preview and full-render records;
- each unresolved binding independently yields `UNKNOWN`;
- `MISMATCH`, denied/expired resource, blocked preflight and Job state drift;
- wrong route, usage, script digest, preflight digest, resource digest,
  destination policy or scope;
- one-shot authorization and exact destination constraints;
- revision-parent lineage;
- strict unknown fields and raw boolean rejection;
- classification, effect flag and checksum tamper;
- deterministic round-trip and schema/runtime parity;
- public redaction and schema mirror byte equality;
- no runtime/effect API surface.

## 6. Critic pass 1 — Builder and compatibility

Finding (High): an admission model that accepted a generic Job state could be
created after an external queue/run had already started, hiding duplicate or
orphan execution. Correction: only the exact `REGISTERED` Job state is
admissible; queued/running/unknown states are blocked.

Finding (High): a route-agnostic resource or Owner approval could be replayed
between zero-shot and fine-tuned routes. Correction: preflight and Owner
authorization bind exact route and usage; resource Evidence must use
`LOCAL_NARRATION_RENDER`; every cross-binding hash is compared.

Finding (High): initially, a valid preflight for different script/Profile
coordinates or a registered durable Job carrying an unrelated operation
identity could be substituted. Correction: preflight now binds exact script,
VoiceProfile and expiry; resource binds route plus preflight hash; the durable
Job operation identity is deterministically derived from the complete render
coordinate; Owner authorization additionally binds VoiceProfile and Job
revision hashes.

Residual Critical/High/Medium: `0 / 0 / 0`.

## 7. Critic pass 2 — Security and privacy

Finding (High): a logical output URI would invite absolute path, traversal or
credential leakage. Correction: the contract carries an opaque destination ID
and exact storage/quota/recovery/retention policy hashes only. The canonical
storage owner remains external.

Finding (Medium): `READY` could be mistaken for dispatch authority. Correction:
the state name is explicitly `READY_FOR_EXTERNAL_DISPATCH_GATE`, all effect
flags are schema constants `false`, and no execute/render/dispatch API exists.

Residual Critical/High/Medium: `0 / 0 / 0`.

## 8. Validation receipt

| Gate | Result |
|---|---|
| Focused contract tests | `26 PASS` |
| Windows full regression | `1621 PASS / 1 non-Windows SKIP` |
| WSL2 full regression | `1621 PASS / 1 Windows-only installer SKIP` |
| Python compile | `PASS` |
| JSON Schema parse/runtime validation | `PASS` |
| Schema mirror byte equality | `PASS` |
| `git diff --check` | `PASS` |

No CMake/native dependency, provider/network client, filesystem/audio access,
model loader, GPU reservation, Job dispatcher or Asset publisher was added.

## 9. Judge

- Domain contract: `PASS`
- Hosted-preflight compatibility: `PASS`
- Body-free/public-private boundary: `PASS`
- Deterministic classification and tamper handling: `PASS`
- Runtime/audio/model/Asset effect: `BLOCKED_BY_DESIGN`
- Residual Critical/High/Medium: `0 / 0 / 0`

The unit is ready for focused/full/hosted validation. Actual Local Primary
engine acquisition, model/license admission, model load, GPU reservation,
synthesis, WAV persistence, QA, Asset publication and production use remain
separate effect units and Human/license/Consent gates where applicable.
