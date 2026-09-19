# TASK-098 A2-R1 Runtime Integration Design and Allocation

- Status: `ACCEPTED / A2-R1A_COMPLETE / A2-R1B_IMPLEMENTATION_ALLOCATED`
- Date: `2026-09-19`
- Governance: `DEV-3 HIGH ASSURANCE`
- Base: `0189676a0f396755f71b11f97a61325cdd0ebef4`
- Authority: Owner AUTONOMY instruction for staged UWR integration
- Effects: Product source/schema/runtime/native/private mutation = `false`

## 1. Decision

A2-R1 is split into three serial Atomic Units:

1. `A2-R1a` — typed capability observation and deterministic decision resolver;
2. `A2-R1b` — shared TASK-036 operation engine and durable runtime-managed v2;
3. `A2-R1c` — explicit trusted-launch composition and public projection.

The Units are not parallel. R1b depends on accepted R1a; R1c depends on accepted
R1b. This document authorizes no implementation until independent review accepts
the design and exact R1a allocation.

## 2. Canonical owner and compatibility boundary

- Existing `FasterWhisperConfig.device/compute_type`,
  `FasterWhisperProvider`, `Task036LocalTranscriptionPort`, command type
  `task036.local_transcription`, operation contract `1.0.0` and publication-set
  `1.0.0` remain the legacy owner path. Their identity, Provider construction,
  output and recovery bytes remain unchanged. R1b adds only a symmetric
  cross-version admission exclusion before either façade may enter Provider.
- No legacy config, operation, saved setting or durable row is converted,
  re-keyed, replayed or reinterpreted as v2.
- Successor Product execution uses the explicit façade
  `Task036RuntimeManagedLocalTranscriptionPortV2` and command type
  `task036.local_transcription.v2`.
- The two façades do not duplicate the state machine. Both delegate source
  snapshot, reservation, output-slot ownership, publication, recovery and final
  binding to one internal `_Task036LocalTranscriptionOperationEngine`.
- Runtime differences are isolated behind `_LegacyRuntimeBindingV1` and
  `_RuntimeManagedBindingV2` strategies. These internal names do not create a
  second Provider or Transcript authority.
- TASK-023 `config_sha256` and `execution_sha256` remain diagnostic identities.
  They never replace the TASK-036 operation key.

## 3. V2 static settings and Provider construction

`FasterWhisperProviderSettingsV2` has only:

- `model`;
- `beam_size`;
- `vad_filter`;
- private `cache_directory`.

It has no `device`, `compute_type` or `allow_model_download` field. Download is
constant false. Its public projection exposes only the same body-free model ID,
boolean/capped numeric settings and `custom_cache_directory_configured`; never a
model/cache path.

The v2 façade accepts static settings, `FasterWhisperRuntimeRequestV1`, a typed
capability probe, a Provider factory and an injected clock. It never accepts a
prebuilt Provider.

Only after a fresh READY decision is durably admitted may the façade construct a
temporary `FasterWhisperConfig`. Its `device` and `compute_type` are exactly the
decision effective values; all other fields come from the static settings and
download remains false. The Provider factory receives that config. Its returned
Provider must match exact provider ID, model ID, full config and download=false.
Mismatch is a post-admission terminal PARTIAL result, not a fallback opportunity.

## 4. Typed capability observation and resolver

### 4.1 Probe protocol

`FasterWhisperRuntimeCapabilityProbe` is an injected Protocol with one pure
Product-facing operation:

```text
supports(device, compute_type) -> bool
```

Allowed pairs are only `cpu/int8` and `cuda/float16`. The coordinator owns the
call order:

| Request | Calls | Result rule |
|---|---|---|
| `cpu` | fake `cpu/int8` only | true READY_CPU; false CPU_UNAVAILABLE |
| `cuda` | fake `cuda/float16` only | true READY_CUDA; false CUDA_UNAVAILABLE |
| `auto` | fake `cuda/float16`, then only when false fake `cpu/int8` | CUDA true READY_CUDA; CUDA false and CPU true READY_CPU fallback; both false BLOCKED |

An exception becomes `RUNTIME_PROBE_UNAVAILABLE`. A non-boolean response,
unsupported pair or structural violation becomes `RUNTIME_PROBE_INVALID`.
Neither error permits auto CPU fallback. R1a accepts only an injected fake probe
in implementation and tests. It does not implement, select or execute a real
OS/GPU/DLL adapter. A real adapter remains a later Human-gated Unit.

### 4.2 Capability observation

`FasterWhisperRuntimeCapabilityObservationV1` has exactly:

- `record_type = FasterWhisperRuntimeCapabilityObservationV1`;
- `schema_version = 1.0.0`;
- `runtime_request_sha256`;
- `probe_outcome = OBSERVED | RUNTIME_PROBE_UNAVAILABLE | RUNTIME_PROBE_INVALID`;
- `cpu_capability = AVAILABLE | UNAVAILABLE | NOT_PROBED | UNKNOWN`;
- `cuda_capability = AVAILABLE | UNAVAILABLE | NOT_PROBED | UNKNOWN`;
- `observed_at` and `expires_at`, UTC `Z`, second precision, TTL `1..300`;
- `model_load_started = false`;
- `inference_started = false`;
- `network_used = false`;
- `model_download_authorized = false`;
- `record_sha256`.

Its digest is lowercase `sha256:<64 hex>` over domain
`bvp.task098.faster-whisper-runtime-capability.v1\0` plus canonical sorted-key
JSON without `record_sha256`. Request-specific probe result combinations are a
closed schema/runtime matrix. Unknown fields and tamper fail closed.

Observation create/parse accepts the validated request object, not an independent
request digest/device pair. The decision resolver accepts that same validated
request and one bound observation. It derives the unique A2-R0 decision. Callers
cannot supply outcome, reason, effective mode or fallback. Decision issue/expiry
equal the observation window.

The exact request-specific observation rows are:

| Request | Probe outcome | CPU capability | CUDA capability | Meaning |
|---|---|---|---|---|
| `cpu` | OBSERVED | AVAILABLE | NOT_PROBED | READY_CPU |
| `cpu` | OBSERVED | UNAVAILABLE | NOT_PROBED | CPU_UNAVAILABLE |
| `cpu` | probe error | UNKNOWN | NOT_PROBED | BLOCKED, no fallback |
| `cuda` | OBSERVED | NOT_PROBED | AVAILABLE | READY_CUDA |
| `cuda` | OBSERVED | NOT_PROBED | UNAVAILABLE | CUDA_UNAVAILABLE |
| `cuda` | probe error | NOT_PROBED | UNKNOWN | BLOCKED, no fallback |
| `auto` | OBSERVED | NOT_PROBED | AVAILABLE | READY_CUDA |
| `auto` | OBSERVED | AVAILABLE | UNAVAILABLE | READY_CPU, fallback true |
| `auto` | OBSERVED | UNAVAILABLE | UNAVAILABLE | AUTO_NO_RUNTIME_AVAILABLE |
| `auto` | probe error on CUDA | NOT_PROBED | UNKNOWN | BLOCKED; CPU not called |
| `auto` | probe error on CPU after CUDA false | UNKNOWN | UNAVAILABLE | BLOCKED; no fallback |

Each `probe error` row is separately exercised for
`RUNTIME_PROBE_UNAVAILABLE` and `RUNTIME_PROBE_INVALID`. No other row is valid.

## 5. Durable v2 identity

The v2 execution-config digest is lowercase `sha256:<64 hex>` over domain
`bvp.task098.task036-runtime-execution-config.v2\0` plus canonical sorted-key
JSON with exactly these keys:

- `contract_version = 2.0.0`;
- `provider_id` and body-free `model_id`;
- `model_config_sha256`;
- `beam_size` and `vad_filter`;
- `cache_directory_sha256` or null;
- `language`;
- `timeline_rate = {numerator, denominator}`;
- `runtime_request_sha256`;
- `model_download_authorized = false`.

`model_config_sha256` hashes the exact private configured model locator. Cache
identity hashes the trusted launcher's normalized absolute cache locator after
`expanduser`, platform-native normalization and non-strict canonical resolution;
the raw locator never leaves private state. Null remains null. It contains no
legacy device or compute field.

The v2 operation key is `task036-transcription-` plus lowercase SHA-256 over
domain `bvp.task098.task036-runtime-operation.v2\0` and canonical JSON with
exactly `contract`, `project_id`, `source_asset_id`, `source_asset_sha256`,
`provider_id`, `model_id`, `execution_config_sha256`,
`runtime_request_sha256` and `model_download_authorized=false`. `contract` is
`task036-local-transcription/2.0.0`.

Different runtime requests or static settings produce different v2 keys. A
short-lived observation or decision digest never participates in the key.

## 6. Admission linearization

The exact v2 sequence is:

1. authorize static settings, output-root policy and construct v2 identity;
2. run the existing fixed-output target preflight and create the canonical
   checksum-verified source snapshot; no durable or Provider effect has started;
3. audit historical opposite-version rows that predate the neutral guard; a
   conflict blocks before creating any v2 row;
4. reserve and CAS-acquire the source-bound version-neutral coordination guard;
   only the guard owner may reserve/find the stable v2 operation as PENDING;
5. run the existing operation-generation target preflight;
6. run the injected fake probe and resolve one observation/decision;
7. inside one store transaction, obtain the injected store clock value, verify
   `issued_at <= evaluated_at < expires_at` and READY, then CAS
   `PENDING + result_ref null -> IN_PROGRESS`, increment attempt and replace
   `result_ref` with
   `task098-runtime-admission:v2:<64 source SHA hex>:<64 decision SHA hex>`;
8. acquire the existing shared fixed-output slot; a slot failure occurs before
   Provider construction and may CAS back to PENDING while clearing the stale
   decision reference;
9. construct the concrete effective config and Provider, then run the shared
   engine;
10. on success, bind v2 publication Evidence before replacing `result_ref` with
   the publication-set SHA.

Step 7 is the admission linearization point. BLOCKED, missing or stale decisions,
including expiry equality, leave the operation PENDING and perform zero Provider
factory/model/inference calls. Expiry after successful step 7 does not revoke the
admitted operation and never triggers re-probe.

Provider construction, model load, `transcribe`, lazy segment iteration or any
later failure changes IN_PROGRESS to PARTIAL while retaining the typed admission
reference until a publication-set ref is durably bound. The reference exposes no
path/body and lets collision classification match the canonical source hash even
without a publication. No CPU reconstruction,
automatic retry, partial reuse or new operation is allowed.

## 7. Publication and recovery

Publication-set v2 extends the immutable set with exact:

- complete body-free serialized runtime request, capability observation and
  decision records, including their record SHA-256 and decision issue/expiry;
- typed admission reference and the store-returned `admission_evaluated_at`;
- v2 execution-config SHA-256;
- TASK-023 config/execution SHA-256 calculated from the actual effective
  Provider config;
- `model_download_authorized = false`.

The diagnostic TASK-023 values do not affect the operation key. Recovery parses
and validates the complete request -> observation -> decision chain, recomputes
every digest, verifies the typed admission reference and proves
`decision.issued_at <= admission_evaluated_at < decision.expires_at`. It checks
freshness at the historical admission instant, never against recovery time, and
uses no probe, factory, model or Provider.
PARTIAL with a publication-set SHA may roll forward Provider-zero. COMPLETED may
only verify/redisplay the exact set. PARTIAL retaining a typed decision ref has
no publication and requires Human adjudication. It cannot re-enter Provider.

## 8. Version-neutral coordination and legacy collision rules

- V1 and v2 have different contract names, command types and keys.
- Both façades share command type
  `task036.local_transcription.cross_version_guard.v1` and one guard key derived
  from Product Job plus canonical Project/source Asset ID/SHA. The guard key has
  no Provider version, config, device or compute input.
- The guard key is `task036-transcription-cross-version-` plus lowercase SHA-256
  over domain `bvp.task098.task036-cross-version-guard.v1\0` and canonical JSON
  with exactly `coordination_version=1.0.0`, `project_id`, `source_asset_id` and
  `source_asset_sha256`. Product Job remains the store uniqueness scope.
- Before guard acquisition, each façade performs a bounded audit only for
  historical opposite-version rows not already represented by a guard. A
  historical conflict blocks before the requester creates its version row. An
  original legacy retry can compute/find its own exact v1 row and then claim an
  absent guard as v1 owner; an opposite v2 attempt cannot.
- Each façade then reserves the same neutral guard and CASes PENDING to
  IN_PROGRESS only when `result_ref` is null. The guard is a permanent
  source-bound **version namespace lease**, not ownership of one execution
  config or operation. Its immutable owner ref is
  `task098-runtime-owner:<v1|v2>:<64 guard-key SHA hex>`, where the final digest
  is the digest already embedded in the guard key. First durable CAS assigns the
  source to v1 or v2. An opposite-version loser returns
  `CROSS_VERSION_OWNER_EXISTS` and creates no v1/v2 operation row.
- A request whose version matches the immutable lease may continue to its own
  existing/new stable operation. Different same-version configs and operation
  keys retain their existing v1 semantics (and the v2 key semantics in section
  5); the normal output-slot and operation rules still serialize or reject them.
  A different version or source identity cannot adopt the guard.
- This guard-first ordering makes simultaneous cross-process v1/v2 start safe:
  one owns; one leaves no losing PENDING row. It also prevents the
  pre-existing-v1-PENDING -> v2-attempt -> v1-retry mutual deadlock.
- An opposite-version PENDING, IN_PROGRESS or FAILED row is opaque because its
  hashed key cannot safely reveal source identity. Its presence in the same
  Product Job therefore blocks the requesting façade and requires Human review.
- Opposite-version PARTIAL/COMPLETED is matched through immutable publication-set
  and output-slot identity. A same-source match blocks the requesting façade and
  routes only to that version's explicit Provider-zero recovery/verification.
- A PARTIAL/FAILED v2 row with a well-formed typed admission reference is matched
  by its bound canonical source SHA. It blocks the same source; different sources
  remain eligible after the shared slot is safely available. A malformed/missing
  reference remains opaque and blocks the Product Job.
- Any unknown/corrupt status, command, reference or publication identity fails
  closed and blocks both façades. No state grants migration, replay, key
  conversion or Provider entry through the other version.

The guard remains IN_PROGRESS as a command-specific permanent version lease;
it does not mirror any individual same-version operation state or result ref.
Its `result_ref` always remains the immutable version/guard-key owner ref, so a
v1 PARTIAL whose operation `result_ref` is null does not erase provenance and a
later same-version config does not overwrite another operation's truth. The
guard is never completed, failed, deleted, reset to a competing owner or
released for the other version. Individual PENDING/PARTIAL/COMPLETED/FAILED
truth remains exclusively on the version operation row. A missing, malformed or
source-mismatched lease binding is `CORRUPT_BLOCKED`.

This conservative opaque-row rule may reduce availability but avoids a
false-negative duplicate Provider execution before or after either version
completes. A future UX relaxation requires a separate migration design.

## 9. Store decision

No SQLite schema/table/column/user-version migration is allocated. Existing
status, attempt, command type, key, error and result-ref fields are sufficient.

R1b may add only:

- a generic freshness-aware CAS that evaluates a supplied UTC validity window
  with the injected store clock inside the same transaction and returns its
  `evaluated_at`;
- a generic bounded read by exact job and caller-supplied command-type prefix,
  returning all statuses without a status filter. R1b passes prefix
  `task036.local_transcription`, classifies the exact known set
  `task036.local_transcription`, `task036.local_transcription.v2`,
  `task036.local_transcription.cross_version_guard.v1` and the existing
  `task036.local_transcription_output_slot`, rejects every other matching command,
  rejects every status outside the exact store allowlist and fails closed when
  the caller-supplied bound is exceeded. Output-slot rows are known coordination
  records, not opposite-version source operations.

Existing schema-version tests must prove the DB version and columns unchanged.
The new APIs must remain generic and may not encode TASK-098 semantics in the
store.

## 10. Atomic implementation allocations

### 10.1 A2-R1a — typed capability and deterministic resolver

- Depth: `DEV-3 HIGH ASSURANCE`.
- Model route: Terra implementation; Luna schema/tests/docs; Sol
  architecture/Critic/completion review.
- No OS/GPU/DLL implementation, Provider, TASK-036, store or launcher mutation.

Allowed files:

- `src/ai_video_production/faster_whisper_runtime_contract.py`
- `src/ai_video_production/faster_whisper_runtime_preflight.py`
- `schemas/faster-whisper-runtime-contract.schema.json`
- `src/ai_video_production/schema_resources/faster-whisper-runtime-contract.schema.json`
- `tests/test_task098_faster_whisper_runtime_contract.py`
- `tests/test_task098_faster_whisper_runtime_preflight.py`
- `docs/ai-team/current-state.md`
- `docs/ai-team/task-index.md`
- `docs/ai-team/tasks/TASK-098/task.md`
- `docs/ai-team/tasks/TASK-098/a2-r1-runtime-integration-design-20260919.md`
- `docs/ai-team/tasks/TASK-098/evidence/a2-r1a-runtime-preflight-20260919-r01.md`

Acceptance:

1. observation runtime/schema/mirror/hash/round-trip/tamper/unknown checks PASS;
2. every request-specific observation row above PASS;
3. exact probe pair and ordering PASS;
4. explicit CPU never calls CUDA and explicit CUDA never calls CPU;
5. only auto CUDA false plus CPU true yields fallback;
6. exception/non-boolean/invalid pair resolves BLOCKED with no fallback;
7. resolver uniquely derives an A2-R0 decision bound to the same request/window;
8. model factory/load, Provider, inference, network and download call count is zero;
9. TTL `1` and `300` seconds are accepted; `0` and `301` are rejected;
   freshness accepts equality at `issued_at` and rejects equality at
   `expires_at`;
10. A2-R0 and TASK-006/023/036 focused regression PASS;
11. independent Critic/Tester report zero unresolved Critical/High;
12. independent Judge returns ACCEPT;
13. durable Evidence is persisted and read back.

### 10.2 A2-R1b — shared engine and durable v2

Depends on accepted R1a. It requires a fresh pre-mutation review.

Allowed-file ceiling for that later review:

- `src/ai_video_production/task036_product_ports.py`
- `src/ai_video_production/store.py`
- `src/ai_video_production/faster_whisper_asr.py`
- `src/ai_video_production/faster_whisper_reconciliation.py`
- `tests/test_task098_task036_runtime_managed_transcription.py`
- `tests/test_task036_local_transcription_operation.py`
- `tests/test_task023_faster_whisper_reconciliation.py`
- `tests/test_idempotency.py`
- bounded TASK-098/current-state/task-index docs.

Acceptance must cover unchanged v1 identity/output/recovery behavior plus the
new symmetric exclusion, v2 identity, reserve-before-probe,
transaction-time expiry, exactly-one cross-thread/process factory entry, blocked/
stale/slot-busy zero factory, post-admission terminal PARTIAL, every legacy state,
every v2 state, unknown/corrupt-state fail-closed behavior, complete serialized
admission chain in publication identity, historical-admission freshness,
Provider-zero recovery, diagnostic-vs-operation identity,
unchanged DB schema/user version and fake-only execution. Tests must include a
v1/v2 cross-process simultaneous start, same-version different-config/key
executions retaining legacy semantics, pre-existing v1 PENDING followed by a
v2 attempt and original-v1 retry, crash after guard claim but before owner-row
reserve, and each direction after the opposite version reaches
COMPLETED/finalize. Exactly one neutral guard version owns the source; an
opposite-version loser creates no version operation row, while same-version
requests continue under existing operation/output-slot semantics.

The factory must return a newly constructed, unloaded Provider. R1b may add a
read-only `model_loaded` observation to the existing Provider; admission rejects
a prebuilt/preloaded Provider before `transcribe`. Fake tests prove constructor
count exactly one and model-load count zero before shared-engine entry.

R1b also defines `RuntimeManagedLocalTranscriptionOutcomeV2`: the existing
transcription outcome plus an exact validated pair named
`runtime_request_public` and `runtime_decision_public`. They equal, byte-for-key,
the bound A2-R0 request's `to_public_dict()` and decision's `to_public_dict()`;
the pair is revalidated against the typed request/decision before construction
and is not merged or independently caller-supplied. R1c reads
`requested_device` from `runtime_request_public`, and `outcome`, `reason_code`,
`effective_device`, `effective_compute_type` and `fallback_applied` from
`runtime_decision_public`. The pair contains no digest, timestamp, path,
exception or private body. This outcome is the only runtime metadata interface
later consumed by R1c.

R1b additionally defines a pure public recovery classifier with exact states:

- `PENDING_ADMISSION`;
- `ACTIVE_UNKNOWN`;
- `RECOVERABLE_PUBLICATION`;
- `VERIFICATION_ONLY`;
- `ADJUDICATION_REQUIRED_NO_PUBLICATION`;
- `FAILED_TERMINAL`;
- `CORRUPT_BLOCKED`.

Only `RECOVERABLE_PUBLICATION` may expose the existing recover action.
`VERIFICATION_ONLY` verifies/redisplays. A PARTIAL typed-admission ref maps to
`ADJUDICATION_REQUIRED_NO_PUBLICATION`; it never calls existing recovery and
keeps the shared slot locked until a separately authorized Human adjudication
contract resolves the uncertain Provider boundary.

### 10.3 A2-R1c — trusted launch composition

Depends on accepted R1b. It requires a fresh pre-mutation review.

Allowed-file ceiling for that later review:

- exact TASK-036 trusted launcher, first-run bootstrap and pre-edit runtime files;
- their exact focused tests;
- bounded TASK-098/current-state/task-index docs.

Legacy launch versions route only v1. R1c composes v2 with an injected fake
adapter in tests but does not activate a production/native v2 route. When the
real adapter dependency is absent, any v2 launch-config request fails closed
before Project/store/Provider effects. A new explicit launch-config version may
be accepted and activated only by the later Human-gated native/A6 adapter Unit;
it routes only v2 and cannot carry legacy compute authority. Direct JavaScript
cannot set device, compute, download or private paths. The bridge consumes only
`RuntimeManagedLocalTranscriptionOutcomeV2` and exposes requested/outcome/reason/
effective/fallback plus constant false privacy/effect flags, with no digest,
timestamp, exception or path.

R1c must replace the legacy boolean recovery presentation for v2 with the exact
classifier above. `ADJUDICATION_REQUIRED_NO_PUBLICATION`, `ACTIVE_UNKNOWN`,
`FAILED_TERMINAL` and `CORRUPT_BLOCKED` expose no recover control and never call
`recover_local_media`. Fake UI/application tests prove the truthful label and
zero recovery/Provider calls.

### 10.4 A2-R2 — progress, cancel and Human adjudication (not allocated)

TASK-098 still owes truthful progress/cancel behavior from the original A2
scope. It is deliberately not hidden inside R1a/b/c. A fresh later design must
own phase-only progress (no fabricated percentage), cancel-before-effect,
cooperative post-start cancellation boundaries, durable cancel outcome,
typed-admission PARTIAL Human adjudication and safe slot release. It must never
represent an unconfirmed Provider stop as cancelled and must preserve no-replay.

A2-R2 is a mandatory dependency before any real/native v2 activation. It has no
implementation authority or allowed files in this checkpoint.

## 11. Human gates and prohibited effects

R1a/R1b/R1c implementation tests are fake-only. Real CTranslate2/GPU probing,
model construction/inference, private audio, packaged launch, installation,
download, Release, Deploy and Production Activation remain separate explicit
native/Human gates. No Unit may weaken download=false or the existing
transcription Human confirmation.

## 12. Design checkpoint allowed files and acceptance

This design checkpoint may modify only:

- `docs/ai-team/current-state.md`;
- `docs/ai-team/task-index.md`;
- `docs/ai-team/tasks/TASK-098/**`.

Acceptance requires independent DEV-3 Critic, Tester and Judge; zero unresolved
Critical/High; exact R1a allocation; durable Evidence/read-back; and no Product
source/schema/runtime/native/private effect. Only accepted R1a becomes
implementation-eligible.

## 13. Review outcome

- Independent Architect: design completed after bounded TASK-006/023/036
  contract inspection.
- Independent Critic: iterative findings closed; final
  `0 Critical / 0 High / 0 Medium / 0 Low / ACCEPT`.
- Independent Tester: `PASS`, final unresolved findings `0/0/0/0`.
- Independent Judge: `ACCEPT`; only A2-R1a is implementation-allocated.
- Product source/schema/runtime/native/private effects: `NOT_EXECUTED`.
- R1b, R1c, A2-R2 and every real/native adapter remain unallocated.

## 14. A2-R1a implementation outcome

- Result: `PASS / COMMIT_READY`.
- Focused R1a+A2-R0 tests: `129 PASS`.
- R1a plus TASK-006/023/036 direct-dependency regression: `168 PASS`.
- Independent Critic: initial `0/0/1/2`, final `0/0/0/0 / ACCEPT`.
- Independent Tester: `PASS / 129 PASS / 0/0/0/0`.
- Independent Judge: `ACCEPT / 0/0/0/0`.
- Real probe, Provider/model, network/download, TASK-036/store/launcher,
  native/private and training effects: `NOT_EXECUTED`.
- R1b remains implementation-unauthorized until its fresh DEV-3 pre-mutation
  review accepts exact allowed files, permanent-lease/store behavior and tests.
