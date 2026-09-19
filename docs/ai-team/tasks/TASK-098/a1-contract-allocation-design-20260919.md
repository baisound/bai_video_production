# TASK-098 A1 Contract Design and Allocation

- Status: `ACCEPTED / A2-R0_IMPLEMENTATION_ALLOCATED`
- Date: `2026-09-19`
- Governance: `DEV-3 HIGH ASSURANCE`
- Base: `4a49364a96e4bbb3d1543d96b49da07dc8143c32`
- Authority: Owner AUTONOMY instruction for staged UWR integration
- Effects: Product source/schema/runtime/native/private mutation = `false`

## 1. A1 decision

A1 is a design/allocation checkpoint. It does not implement a schema, runtime,
Provider, worker, import adapter or UI. Its purpose is to resolve canonical
ownership before the first implementation Unit.

The first implementation Unit is `A2-R0`, a pure FasterWhisper runtime request/
decision contract. Audio Review integration is not implemented in A2-R0. UWR receipt
compatibility remains dependency-blocked.

## 2. Context escalation and direct dependencies

A0 deferred TASK-041 until review design was required. A1 inspected the exact
TASK-041 media-review contract and found that it owns the existing 48 kHz,
canonical Asset/Candidate, body-free source/capability/intent/external-receipt/
Human-decision boundary. TASK-041 is therefore a direct dependency from A1
forward, but it does not cover arbitrary-rate or not-yet-adopted WAV files. A4 is
limited to the existing TASK-041 admission domain; no second durable
`bvp.audio-review.v1` store or implicit TASK-041 source-contract expansion is
permitted.

The minimal A1 source set is:

- TASK-006/023 FasterWhisper config, Provider and Transcript identity;
- TASK-036 `Task036LocalTranscriptionPort` durable operation identity/recovery;
- TASK-041 `bai.task041.audio-workspace-media-review.v1` and focused tests;
- Subtitle Workspace and canonical Transcript Manifest boundaries;
- exact TASK-047 candidate-ABI and TASK-048 quality-ownership sections;
- UWR v1.0.5 reference design only.

## 3. Canonical ownership matrix

| Concern | Canonical owner | TASK-098 allocation |
|---|---|---|
| ASR request, Transcript, SRT | TASK-006 | consume unchanged |
| FasterWhisper provider/model identity | TASK-023 over TASK-006 implementation | extend only through bounded provider Units |
| durable Product transcription operation, fixed output and recovery | TASK-036 | keep one stable semantic request key; bind a short-lived decision to that operation without key rotation |
| 48 kHz canonical Asset/Candidate audio source/capability/range/review intent/external receipt/Human decision | TASK-041 | reuse records and public projection; arbitrary WAV first needs its existing canonical ingest/normalization route |
| editable subtitle text and review revision | TASK-006 Subtitle Workspace | present through an ephemeral coordinator; no second text store |
| Voice Dataset/Training/ModelCandidate | TASK-046 | no TASK-098 mutation |
| capture provenance and future exact receipt ABI | TASK-047 | foreign UWR receipt remains unsupported/opaque |
| voice quality, calibration and Dataset eligibility | TASK-048 | consume exact Evidence only; no TASK-098 quality decision |

## 4. Runtime request and decision contracts

### 4.1 Purpose

`FasterWhisperRuntimeRequestV1` is the stable semantic request. Its digest may
participate in TASK-036 exactly-once identity. `FasterWhisperRuntimeDecisionV1`
is a short-lived body-free preflight receipt that resolves that request before
model construction. The decision digest never participates in the operation key.
Neither record grants Provider execution or model-download authority.

Both contracts are separate from `TranscriptManifest`. Transcript remains output
truth.

### 4.2 Exact request record

`FasterWhisperRuntimeRequestV1` has exactly these fields:

| Field | Exact contract |
|---|---|
| `record_type` | constant `FasterWhisperRuntimeRequestV1` |
| `schema_version` | constant `1.0.0` |
| `requested_device` | `auto | cpu | cuda` |
| `compute_policy` | constant `UWR_BALANCED_V1` |
| `model_download_authorized` | constant `false` |
| `record_sha256` | lowercase `sha256:<64 hex>` deterministic digest defined in 4.6 |

`UWR_BALANCED_V1` resolves CPU to `int8` and CUDA to `float16`; no other
compute type belongs to A2-R0. Adding a compute type or policy requires a new
contract version and review, not an unbounded string.

### 4.3 Exact decision record

`FasterWhisperRuntimeDecisionV1` has exactly these fields:

| Field | Exact contract |
|---|---|
| `record_type` | constant `FasterWhisperRuntimeDecisionV1` |
| `schema_version` | constant `1.0.0` |
| `runtime_request_sha256` | exact request `record_sha256` |
| `outcome` | `READY_CPU | READY_CUDA | BLOCKED` |
| `reason_code` | one closed value from the matrix below |
| `effective_device` | `cpu | cuda | null`, per matrix |
| `effective_compute_type` | `int8 | float16 | null`, per matrix |
| `fallback_applied` | boolean, per matrix |
| `capability_observation_sha256` | lowercase `sha256:<64 hex>` issued by a future injected body-free probe adapter; A2-R0 validates but does not produce/probe it |
| `issued_at` | UTC RFC 3339 text ending `Z`, second precision |
| `expires_at` | UTC RFC 3339 text ending `Z`, strictly later than `issued_at`, TTL `1..300` seconds |
| `model_load_started` | constant `false` |
| `inference_started` | constant `false` |
| `partial_output_present` | constant `false` |
| `execution_authorized` | constant `false` |
| `record_sha256` | lowercase `sha256:<64 hex>` deterministic digest defined in 4.6 |

The capability observation is a typed future dependency with domain
`BVP_FASTER_WHISPER_RUNTIME_CAPABILITY_V1`; no OS/GPU/DLL producer is allocated
by A2-R0. A2-R1 must allocate the producer and exact observation schema before it
can construct a decision in Product code.

The records intentionally carry no model locator, cache locator, path, exception
text, credential, media identity or transcript body. Unknown fields are rejected.
The A2-R0 public projection contains only schema/record type, requested policy or
outcome/reason/effective device/type/fallback and constant false privacy/effect
flags. It omits all digests and timestamps.

### 4.4 Complete outcome matrix

| Requested device | Outcome | Reason | Effective device/type | Fallback |
|---|---|---|---|---|
| `cpu` | `READY_CPU` | `REQUESTED_CPU_AVAILABLE` | `cpu / int8` | `false` |
| `cpu` | `BLOCKED` | `CPU_UNAVAILABLE` | `null / null` | `false` |
| `cpu` | `BLOCKED` | `RUNTIME_PROBE_UNAVAILABLE` or `RUNTIME_PROBE_INVALID` | `null / null` | `false` |
| `cuda` | `READY_CUDA` | `REQUESTED_CUDA_AVAILABLE` | `cuda / float16` | `false` |
| `cuda` | `BLOCKED` | `CUDA_UNAVAILABLE` | `null / null` | `false` |
| `cuda` | `BLOCKED` | `RUNTIME_PROBE_UNAVAILABLE` or `RUNTIME_PROBE_INVALID` | `null / null` | `false` |
| `auto` | `READY_CUDA` | `AUTO_CUDA_AVAILABLE` | `cuda / float16` | `false` |
| `auto` | `READY_CPU` | `AUTO_CUDA_UNAVAILABLE_CPU_AVAILABLE` | `cpu / int8` | `true` |
| `auto` | `BLOCKED` | `AUTO_NO_RUNTIME_AVAILABLE` | `null / null` | `false` |
| `auto` | `BLOCKED` | `RUNTIME_PROBE_UNAVAILABLE` or `RUNTIME_PROBE_INVALID` | `null / null` | `false` |

Every other cross-product is invalid. `BLOCKED` always has null effective fields
and `fallback_applied=false`. A READY outcome cannot use a probe-error reason.

### 4.5 No-retry invariant

The preflight linearization point is before model construction. After model
construction begins, after `model.transcribe()` is called, or after lazy segment
iteration starts, CUDA failure is terminal for that operation. It may not restart
on CPU, reuse partial output or relabel the operation as fallback success.

Explicit `cuda` never falls back. Explicit `cpu` never probes CUDA. `auto` may
choose CPU only through the exact preflight rule above.

### 4.6 Digest, freshness and TASK-036 identity

Each record digest has the exact wire form `sha256:<64 lowercase hexadecimal
characters>`. The 64 hexadecimal characters are SHA-256 over UTF-8 canonical
JSON with sorted keys, no insignificant whitespace, and `record_sha256`
excluded. The exact preimages are:

- request: `bvp.task098.faster-whisper-runtime-request.v1\0` followed by the
  canonical JSON bytes;
- decision: `bvp.task098.faster-whisper-runtime-decision.v1\0` followed by the
  canonical JSON bytes.

Admission evaluates the decision at an explicit UTC `evaluated_at`. It is fresh
only when `issued_at <= evaluated_at < expires_at`; equality at expiry is stale.
A stale/missing/BLOCKED decision prevents `PENDING -> IN_PROGRESS` and never
creates a replacement operation.

TASK-036's stable operation key uses the request digest, not the time-varying
decision digest. Its existing `execution_config_sha256` remains the canonical
durable Product identity for model, Provider, cache, beam, VAD, language and
timebase. A2-R0 does not derive a request from, bind to or alter the existing
`FasterWhisperConfig`; its records cannot be admitted to Product execution.

A2-R1 must update the TASK-006/023/036 owner contracts together and advance the
TASK-036 execution-config contract from `1.0.0` to a reviewed successor. In that
successor:

- `runtime_request_sha256` replaces the legacy `device` and `compute_type` fields
  in the operation-key preimage; it is not merely added beside two competing
  authorities;
- the request's `requested_device` and `compute_policy` are the sole device and
  compute policy inputs for a successor operation;
- only after a fresh READY decision is atomically admitted may a Provider config
  be constructed, and its constructor receives exactly
  `decision.effective_device` and `decision.effective_compute_type`;
- publication/recovery evidence binds the request digest, decision digest and the
  same effective device/type, making a `READY_CUDA/float16` decision with an
  `auto/int8` Provider construction invalid;
- TASK-023 `config_sha256` remains diagnostic/reconciliation identity and must be
  recomputed from the actual effective Provider configuration; it is never
  substituted for TASK-036 operation identity.

The existing `FasterWhisperConfig.device/compute_type` pair remains authoritative
only for legacy contract `1.0.0` operations. It is not silently reinterpreted or
auto-migrated. Creating a successor operation requires an explicit successor
request; an existing legacy operation or saved `auto/*` setting never creates one
by conversion. Thus A2-R1 changes the owner contracts explicitly instead of
silently taking TASK-006/023 compute authority.

The short-lived decision digest is bound to the already reserved operation at
admission and to the immutable publication-set/recovery evidence, but never to
the operation key. A2-R1 must define the exact atomic binding before Provider
execution. Existing 1.0 operations are never automatically migrated or replayed.
Any legacy PENDING/IN_PROGRESS/PARTIAL/COMPLETED record for the same stable
Project/source/request blocks automatic successor execution. PARTIAL/COMPLETED
follows the existing Provider-zero recovery path; PENDING/IN_PROGRESS requires
explicit Human adjudication and never auto-enters the Provider. Contract-version
change does not create an automatic re-transcription right.

## 5. Review integration decision

### 5.1 No second review store

The prototype name `bvp.audio-review.v1` is a foreign format label, not a BVP
canonical schema. BVP already has:

- TASK-041 `AudioMediaSourceBinding`;
- `PlaybackWaveformCapabilityBinding`;
- `AudioMediaReviewIntent` with half-open sample range;
- `ExternalAudioReviewReceiptBinding`;
- `AudioMediaReviewDecision`;
- TASK-006 `SubtitleWorkspace` for text revisions.

TASK-098 will not add another durable review session or transcript authority.

A4's initial scope is limited to an already `BOUND_VERIFIED` TASK-041 source
with exact canonical reference/revision, Candidate ID, Asset ID, rights PASS and
48 kHz sample truth. An arbitrary-rate or unregistered WAV is not admitted by
TASK-098. It must first follow the existing BVP ingest/normalization/Asset and
Candidate route under those owners. A4 neither broadens TASK-041 nor creates an
alternate generic-WAV source contract.

### 5.2 Ephemeral coordinator

A later review Unit may build an in-memory/UI ViewModel that joins exact hashes
from TASK-041 with one Subtitle Workspace revision and one canonical Transcript
digest. The ViewModel owns no persistence and no media bytes. Text edits continue
through Subtitle Workspace revision/CAS.

TASK-041 `validate_external_review_inclusion()` proves only that receipt inputs
match intent/source/capability/range; it is not completion proof. A4 must add a
separate TASK-098 completion classifier without weakening TASK-041. Completion
requires all of:

- inclusion classification `ACCEPT_PROVEN_EXTERNAL_REVIEW`;
- `contract_state=BOUND_VERIFIED`;
- `external_state=COMPLETED`;
- `canonical_persistence_verified=true`;
- requested `AUDITION` implies `audition_completed=true`;
- requested `WAVEFORM_VIEW` implies `waveform_available=true`.

`FAILED`, `CANCELLED_SAFE`, `UNKNOWN`, null, false or operation-specific missing
flags remain non-complete even when inclusion succeeds. Human review decisions
must not cite inclusion alone as successful audition/waveform Evidence.

Millisecond subtitle ranges and sample ranges are projections of their canonical
sources. Conversion must use the bound sample rate with explicit half-open
rounding and must never rewrite Transcript microsecond timing or TASK-041 sample
truth.

### 5.3 Foreign review import

Any future `bvp.audio-review.v1` importer is separately allocated and Human-
confirmed. It must be size bounded, reject unknown/unsafe structures, expose no
raw absolute path and emit only existing TASK-041/Subtitle Workspace commands.
Import does not preserve a foreign object as canonical truth and does not replace
Transcript.

## 6. Voice Capture receipt boundary

The UWR receipt name is untrusted foreign metadata. A1, A2 and A4 do not read,
copy or persist its body. Until TASK-047 lands one exact schema/parser under fresh
DEV-4 acceptance, TASK-098 may return only the body-free status
`UNSUPPORTED_FOREIGN_RECEIPT`. It may not:

- parse fields into TASK-047 truth;
- validate or promote a filename/hash/byte count as canonical capture identity;
- copy the receipt verbatim into review JSON;
- emit quality, calibration or Dataset-eligibility conclusions;
- authorize recording, Dataset adoption or training.

A5 remains blocked. This A1 design creates no TASK-047 start receipt.
Any future private quarantine/custody capability requires a separate Unit, Human
gate, size/type bounds, encryption/ACL, retention/deletion rules and canonical
custody owner; none is allocated here.

## 7. Atomic implementation allocation

### A2-R0 — pure runtime-decision contract

- Development depth: `DEV-3 HIGH ASSURANCE`.
- Model route: Implementation capability (`GPT-5.6 Terra`) for code; Bulk /
  Mechanical (`GPT-5.6 Luna`) for schema fixtures/tests/docs; High-Reasoning
  (`GPT-5.6 Sol`) for contract Critic and completion review.
- Goal: implement only immutable runtime-request/decision values, deterministic
  hashing, canonical validation, public projection and schema mirror.
- No OS/GPU/DLL probe, Provider construction, inference, retry, download or UI.

Allowed files for A2-R0:

- `src/ai_video_production/faster_whisper_runtime_contract.py`
- `schemas/faster-whisper-runtime-contract.schema.json`
- `src/ai_video_production/schema_resources/faster-whisper-runtime-contract.schema.json`
- `tests/test_task098_faster_whisper_runtime_contract.py`
- `docs/ai-team/current-state.md`
- `docs/ai-team/task-index.md`
- `docs/ai-team/tasks/TASK-098/**`

Acceptance for A2-R0:

1. both record types pass schema/runtime/mirror round-trip and byte equality;
2. exact domain-separated digest preimages, deterministic hash and tamper/
   unknown-field rejection PASS;
3. exact request field grammar, request/outcome/reason/nullability/fallback matrix PASS;
4. explicit CUDA never falls back and explicit CPU never claims a CUDA probe;
5. post-start/partial-output states can never produce READY/fallback;
6. paths, traversal, media/transcript bodies, exception text, credentials, model/
   cache locators and unknown fields are unrepresentable; digests/timestamps are
   suppressed from public projection;
7. all authority/effect flags are fixed false;
8. freshness boundaries `issued <= evaluated < expires` and TTL `1..300` PASS;
9. focused TASK-098 plus TASK-006/023 identity regression PASS;
10. independent Critic/Tester report zero unresolved Critical/High;
11. durable Evidence is persisted and read back.

### A2-R1 — provider and TASK-036 integration

Separately allocated after A2-R0. It will require a fresh overlap audit and its
own allowed files because it modifies the canonical Provider and durable
operation identity/state machine. It must preserve a stable request-keyed
exactly-once reservation, atomically bind one fresh decision before Provider use,
bind the decision to immutable publication/recovery Evidence and block automatic
replay of existing 1.0 operations. Tests use injected fake probes/models only.

### A4 review coordination

Separately allocated after runtime/model foundations. It reuses TASK-041 and
Subtitle Workspace; it does not create `bvp.audio-review.v1` as a BVP store.

### A5 receipt compatibility

`DEPENDENCY_BLOCKED / DEV-4 MINIMUM`. It cannot start before the exact TASK-047
ABI/parser and prerequisites are canonical and independently accepted.

## 8. A1 allowed files

- `docs/ai-team/current-state.md`
- `docs/ai-team/task-index.md`
- `docs/ai-team/tasks/TASK-098/task.md`
- `docs/ai-team/tasks/TASK-098/a1-contract-allocation-design-20260919.md`
- `docs/ai-team/tasks/TASK-098/evidence/a1-contract-allocation-20260919-r01.md`

## 9. A1 acceptance

- canonical ownership includes TASK-041 without changing A0 history;
- runtime decision and no-retry/fallback invariants are closed;
- review reuses TASK-041 and Subtitle Workspace without a second store;
- foreign UWR receipt remains unsupported/opaque and A5 remains DEV-4 blocked;
- A2-R0 goal, depth, model route, allowed files and acceptance are exact;
- independent Critic, Tester and Judge accept with zero unresolved Critical/High;
- documentation checks and focused policy contracts PASS;
- durable external Evidence is persisted and read back;
- no Product source/schema/runtime/native/private effect occurs in A1.

## 10. A1 completion

- Independent Critic first pass: `0 Critical / 4 High / 1 Medium / 0 Low`.
- Independent Critic second pass: `0 Critical / 1 High / 2 Medium / 0 Low`.
- Corrections closed the stable-request/short-lived-decision split, exact outcome
  matrix, TASK-036 successor identity, legacy device/compute non-migration,
  digest wire form, TASK-041 completion classifier and 48 kHz scope, plus the
  unsupported-only foreign receipt boundary.
- Independent Critic final: `0 Critical / 0 High / 0 Medium / 0 Low`, `ACCEPT`.
- Independent Tester: design/diff/scope checks `PASS`; no unresolved
  Critical/High.
- Independent Judge: `ACCEPT`, `0 Critical / 0 High / 0 Medium / 0 Low`.
- Direct-dependency regression: `40 PASS` under the existing WSL Ubuntu Python
  environment. Windows Python dependency availability was initially
  `NOT_CONFIRMED`; no package installation was performed.
- Product source/schema/runtime/native/private effects: `NOT_EXECUTED`.
- Evidence: `evidence/a1-contract-allocation-20260919-r01.md`.

A2-R0 is now the only implementation Unit allocated by A1. A2-R1, A3, A4 and
A5 retain their separate allocation and Human/dependency gates.
