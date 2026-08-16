# TASK-035 REAPER Audio Finishing Foundation R0 — Design / Evidence / Critic / Judge

## 1. Authority and result

- Authority: `OWNER-AUTH-20260817-DEVELOPER2-EXCLUSIVE-ROADMAP-QUEUE-AUTONOMY-01`
- Unit: TASK-035 REAPER Audio Finishing Foundation R0
- Implementation class: pure, body-free metadata/schema/evaluator
- Canonical audit base: `main@a45337ab4a10fa4e29c4ad23d7e419b0b021ba63`
- Repository effect scope: the five task-owned paths listed below plus a separately serialized one-line CHANGELOG composition
- Runtime effect scope in this unit: none

This unit does not launch or operate REAPER, read or write `.rpp` or audio files, scan/insert/configure plug-ins, render, analyze audio, promote Assets, modify Resolve, or authorize Release/Deploy/Production.

## 2. Fresh allocation audit

At transaction start:

- open pull requests: 0
- Registry revision: 23
- active lock: `BVP-LOCK-TASK046-PVS3B` only
- overlap between that lock and the TASK-035 paths: 0
- target branch/worktree and all five task-owned paths: absent
- CHANGELOG preimage blob: `d0149ea67546536e6323ccbfc2024e4c774d5c25`
- TASK-047, TASK-048, TASK-016, TASK-020 and TASK-021 completed implementations are dependencies only and are not reopened

The installed REAPER executable was observed read-only as version 7.78 on Windows x64, 18,438,216 bytes, with digest `sha256:13f34a0839ccf84fc80b99c5c08ad25e59b721dff009e9b55659da1e7d888379`; REAPER was not running. The executable location is private and is not recorded here. This observation does not prove ReaScript, project write, undo, render, plug-in, license, or end-to-end compatibility. Those states remain `PROBE_REQUIRED` or `UNKNOWN` until a separately authorized runtime probe and applicable Human/license gate.

## 3. Existing truth and missing-contract matrix

| Concern | Existing canonical owner | R0 behavior |
|---|---|---|
| Asset identity, rights and immutable revisions | TASK-003 | exact `DawSourceBinding` reference; no Asset truth or promotion |
| Timeline audio intent and placement | existing timeline-audio contract | exact digest reference; no placement mutation |
| Audio Workspace state | TASK-041 | exact digest reference; no duplicate workspace state |
| CPU/RAM/disk/process/app admission | TASK-020 | exact admission digest; no OS collector/reservation |
| Raw/capture acoustic QA | TASK-048 | external `AudioQaReceiptBinding`; no analyzer execution |
| DAW project/track/route/render intent | missing | immutable `DawSessionPlan` with deterministic digests |
| REAPER/version/API/render/plug-in facts | missing | `DawCapabilityReport`; facts never imply authority |
| Human-owned project safety | partial task design | explicit ownership, snapshot and one-shot authorization binding |
| Render/QA/Owner approval/Asset/Resolve return | missing | append-only `AudioRoundTripManifest` state ladder |

## 4. Canonical serialized types

The public schema and module support exactly ten root records:

1. `DawFinishingPolicyRevision`
2. `DawSourceBinding`
3. `DawCapabilityReport`
4. `DawSessionPlan`
5. `DawExecutionAuthorizationBinding`
6. `DawProjectSnapshotBinding`
7. `DawExecutionReceiptBinding`
8. `AudioQaReceiptBinding`
9. `HumanMixApprovalBinding`
10. `AudioRoundTripManifest`

All records reject unknown fields, use canonical JSON and `sha256:<64 lowercase hex>`, and apply closed enums and bounded arrays. Revisions use an exact parent digest from revision 2 onward. Identifiers reject absolute paths, traversal and credential-like values.

## 5. Authority and lifecycle boundaries

`DawSessionPlan` records deterministic source, timeline, workspace, resource, capability, track, route and render-target coordinates. It always has `execution_started=false`. `HUMAN_OWNED` projects cannot be marked automation-preflight-ready.

`DawExecutionAuthorizationBinding` replaces any forgeable boolean. A usable binding requires an exact session/capability/resource/operation scope, `OWNER_HUMAN_GATE`, expiry, evidence, and unused one-shot semantics. The pure evaluator validates this metadata but does not dispatch it.

External execution is represented by `DawExecutionReceiptBinding`. `COMPLETED` requires an after-snapshot and canonical persistence proof. `FAILED`, `CANCELLED_SAFE` and `UNKNOWN` remain distinct. Missing/partial/unobservable data never becomes success.

The round-trip ladder is:

`RENDER_CANDIDATE → QA_VERIFIED → HUMAN_APPROVED → ASSET_BOUND → PLACEMENT_BOUND`

No earlier state grants a later effect. Untreated source preservation is mandatory. Asset promotion, Resolve mutation and publication flags are always false in this metadata unit.

## 6. Acyclic approval lineage

Approval cannot hash a final manifest that itself hashes the approval. The contract therefore uses this append-only DAG:

`candidate AudioRoundTripManifest revision → HumanMixApprovalBinding(candidate_manifest_sha256) → later AudioRoundTripManifest revision(human_approval_sha256)`

The later revision also points to the earlier revision through `parent_record_sha256`. Pre-approval states reject approval hashes, and only `PLACEMENT_BOUND` may carry a Resolve placement-plan hash.

## 7. Preflight classification

`classify_preflight` checks policy currency, 48 kHz policy, capability and source-set exact binding, current rights, required capability facts, license state and plan state. Severity is monotonic:

`READY_FOR_OWNER_HUMAN_GATE < UNKNOWN < BLOCKED`

An UNKNOWN observation can never weaken a proven blocker. The report explicitly keeps launch, project mutation, render, Asset promotion, Resolve mutation and publication false.

## 8. Public/private projection

Private projection is a lossless metadata copy. Public projection exposes only type/hash and safe state/reason fields. It never exposes executable or plug-in inventory hashes, private paths, raw license data, body/media, credentials or reviewer evidence.

## 9. Acceptance and negative inventory

- schema mirror differs by one byte → fail
- unknown root/field, bad enum, cap overflow, duplicate or unsorted binding → reject
- digest tamper or parent/revision mismatch → reject
- absolute/private/traversal/credential coordinate → reject
- unresolved binding invents canonical truth → reject
- plug-in inventory `SUPPORTED` without exact digest, or digest with non-supported state → reject
- human-owned project marked automation-ready → reject
- caller supplies `execution_authorized=true` → reject as unknown field
- expired, consumed, reusable, wrong authority or incomplete execution authorization → reject
- completed execution without after-snapshot or canonical persistence → reject
- UNKNOWN execution with no after-snapshot → retain UNKNOWN, not success
- QA PASS at a non-48-kHz sample rate → reject
- module claims it analyzed audio or performed an effect → reject
- Human approval binds final self-referential manifest → schema/API has no such field
- approval/placement gate jump → reject
- untreated source not preserved → reject
- public projection leaks executable/plugin/private/license coordinates → test failure
- rights revoked plus another UNKNOWN input → final classification remains BLOCKED

## 10. Exact files and validation plan

Task-owned implementation paths:

1. `docs/ai-team/tasks/TASK-035/reaper-audio-finishing-foundation-r0-design-critic-judge.md`
2. `schemas/reaper-audio-finishing.schema.json`
3. `src/ai_video_production/schema_resources/reaper-audio-finishing.schema.json`
4. `src/ai_video_production/reaper_audio_finishing.py`
5. `tests/test_task035_reaper_audio_finishing.py`

Serialized release-metadata composition: `CHANGELOG.md` one `[Unreleased]` bullet under `BVP-ILOCK-20260817-TASK035-R0-CHANGELOG-01`. Registry, roadmap, workflow, `__init__.py`, existing modules, REAPER files and user media are denied.

Validation requires focused tests, schema check and byte-exact mirror, static no-effect scan, Python compile, Windows regression with any managed-sandbox-only denial separately classified, WSL full regression, exact-path diff, hosted checks and post-merge CI/Security.

Local validation result:

- focused TASK-035: 20 passed
- schema draft check and all ten root payloads: passed
- public/schema-resource mirror: byte exact
- Python AST compile and static no-effect scan: passed
- Windows full: 1,543 passed / 1 skipped / 1 unrelated `ProductProjectBackupStore` directory-rename permission failure; immediate isolated single-test reconciliation passed 1/1
- WSL full: 1,544 passed / 1 Windows-only skip

The reconciled Windows permission failure changed no source and is not counted as TASK-035 PASS evidence; the complete WSL suite and hosted Windows checks remain the canonical full-regression gates.

## 11. Critic pass 1

### Builder

Initial finding (High): approval referenced a manifest that would reference the approval, allowing a hash cycle. Corrected to approval of an earlier candidate manifest revision and added a negative/state test.

Initial finding (Medium): fail-closed preflight assignments could allow a later UNKNOWN to overwrite BLOCKED. Corrected with monotonic severity and a revoked-rights-plus-unknown-license test.

Initial finding (Medium): external UNKNOWN/failed receipt was forced to invent an after-snapshot and completion time. Corrected with state-dependent requirements while preserving stricter COMPLETED proof.

### Security

Static surface has no filesystem, subprocess, network, REAPER, provider or analyzer invocation. Absolute paths, traversal, credential-like identifiers, license data and plug-in inventory details are excluded from public projection. No unresolved security finding remains.

## 12. Critic pass 2

### Compatibility / Audio UX

Canonical TASK-035 names `DawSessionPlan`, `DawCapabilityReport` and `AudioRoundTripManifest` remain present. Existing Asset, timeline, workspace, Resource Admission and QA contracts remain authoritative references. A 48-kHz QA PASS cannot be inferred from plan metadata, short probes, installed-version observation or REAPER availability. Human takeover and untreated source retention remain explicit. No existing completed task is modified.

### Independent Judge

- Critical: 0
- High: 0
- Medium: 0
- body/audio/project/runtime effect: 0
- authority inflation: 0
- schema/module mirror drift: 0 after validation
- `PURE_METADATA_FOUNDATION_READY`: PASS
- `REAPER_RUNTIME_AND_LICENSE_READY`: BLOCKED / separate probe and Human gate
- `ASSET_RESOLVE_RELEASE_PRODUCTION_READY`: BLOCKED / separate downstream gates
