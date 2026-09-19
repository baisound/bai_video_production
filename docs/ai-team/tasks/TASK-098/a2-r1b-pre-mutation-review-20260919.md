# TASK-098 A2-R1b Fresh Pre-Mutation Review

- Status: `ACCEPTED / IMPLEMENTATION_ALLOCATED / NOT_STARTED`
- Date: `2026-09-19`
- Active Project / Unit: `BAI VIDEO PRODUCTION / TASK-098 / A2-R1b`
- Depth: `DEV-3 HIGH ASSURANCE` (shared durable state machine and admission boundary).
- Inspected HEAD: `d335dd41a2a426e13c04c1202b1799c61f1fc0ab`; branch: `codex/task-098-universal-wav-review-integration`.
- Base/current local main: `28ba61e5f01047a716c681a3584be22500fe53fc`.
- Worktree: `C:\home\baisound\projects\bai-video-production\.worktrees\task-098-universal-wav-review-integration`.
- Starting worktree: clean. This review changes this document only.
- Authority: Owner staged-integration AUTONOMY instruction; accepted R1 design and completed R1a are dependencies, not R1b implementation authority.

## 1. Scope and current ownership

The review read Current State, TASK-098, accepted R1 design, and only the four
ceiling source files and three existing ceiling tests. The new R1b test file does
not yet exist. No repository-wide or private-media inspection was needed.

Line anchors below refer to the inspected HEAD, before refactoring.

| Owner | Exact current location | R1b responsibility |
|---|---|---|
| TASK-036 local port | `task036_product_ports.py:89`, `Task036LocalTranscriptionPort` | Preserve the public v1 constructor and methods; introduce explicit v2 facade and one shared internal engine. |
| V1 identity | `_authorize_provider:104`, `_operation_key:160` | Preserve exact JSON keys, digest bytes and path treatment for v1. |
| Shared output slot | `_slot_key:183`, `_acquire_output_slot:191`, `_release_output_slot:225` | Keep the existing project/job slot key and binding-only release. |
| Stable input | `_snapshot_source:242`, `_provider_snapshot:306`, `_snapshot_sha256:435` | Reuse descriptor/pinning behavior without weaker source checks. |
| Output boundary | `_pinned_output_directory:443`, `_preflight_output_targets:542`, `_preflight_generation_target:570` | Reuse path/type/size/pinning checks; perform them before their corresponding effects. |
| Canonical publication | `_validate_publication:589`, `_publication_set_body:661`, `_store_immutable_publication_set:687`, `_load_immutable_publication_set:747`, `_promote_publication:834` | One physical read/write/promotion implementation, with exact v1/v2 metadata codecs. |
| Operation lifecycle | `transcribe_local_media:888`, `recover_local_media:1066`, `finalize_local_media_binding:1151`, `recovery_required:1202` | Move lifecycle once into the engine; preserve v1 entrypoint/error/result behavior except accepted version exclusion. |
| Generic persistence | `store.py:848` reserve, `:897` find, `:910` status CAS; `OperationRecord:32` | Add two generic APIs below; no Product-specific commands in store. |
| Provider/model | `faster_whisper_asr.py:30` config, `:75` Provider, `:87` lazy model, `:101` transcribe | Existing Provider only; additive read-only unloaded-state observation. |
| TASK-023 diagnostics | `faster_whisper_reconciliation.py:38` config payload, `:75` identity | Preserve legacy bytes; share a config-only identity route for Provider-zero recovery. |

TASK-006 owns Transcript/SRT/report bytes. TASK-023 owns FasterWhisper and its
diagnostic hashes. TASK-036 owns operation, publication and binding. TASK-098
adds runtime admission inside those owners. TASK-041/046/047/048/097 ownership,
voice training and foreign receipt restrictions are unchanged.

## 2. Shared-engine extraction and compatibility

`_Task036LocalTranscriptionOperationEngine` owns source snapshot, fixed-output
and generation preflight, version coordination, operation reservation/admission,
slot ownership, common execution, immutable publication, recovery and final
binding. `_LegacyRuntimeBindingV1` and `_RuntimeManagedBindingV2` supply version,
identity, admission, Provider creation and metadata validation differences.
Neither facade contains a copied transcribe/recover state machine. Pure helpers
may remain module-local; existing v1 private helper calls used by tests remain
thin delegates where needed.

V1 remains `Task036LocalTranscriptionPort(provider, output_directory, store,
production_job_id, language=None, timeline_rate=...)`. Its caller-supplied
Provider, lazy reuse, `device=auto` legacy meaning, command, contract, operation
key, execution-config digest, slot key, publication-set 1.0.0 bytes, canonical
three output files, failure codes, explicit recovery and final-binding behavior
remain identical for inputs not blocked by the new symmetric exclusion. V1 cache
identity continues hashing `str(cache_directory)`; do not normalize it during
this refactor. No v1 row is rewritten, migrated or re-keyed. Golden tests must
compute expected bytes independently of the refactored helper.

Same-version different settings still produce different operation keys. After
the existing output slot is finalized, a new same-version key may execute under
the same permanent version lease. A lease is not an execution-wide single-flight
lock; exact operation CAS plus the existing output slot provide that lock.

## 3. Permanent version lease and historical audit

Use the exact guard command/key/domain/owner reference from accepted R1 section
8. The guard scope is `(Product Job, Project, source Asset ID, source SHA)`.
It has no Provider settings or operation key. Its only legal stable states are:

| Guard row | Meaning / action |
|---|---|
| Absent | Audit first, then reserve a new PENDING/null row. |
| PENDING + null, attempt 0 | Unassigned; CAS to IN_PROGRESS with exact immutable owner ref. |
| IN_PROGRESS + exact owner ref and matching key digest | Permanent v1 or v2 namespace; matching version continues; opposite version stops. |
| Any other status, malformed ref/key, changed command/job, or mismatched digest | `CORRUPT_BLOCKED`; no repair, release or Provider entry. |

Lease CAS does not increment attempt: attempt stays 0 and the owner ref is
immutable. An opposite loser creates no version operation row. A crash between
guard reserve and CAS leaves a claimable PENDING/null guard. A crash after claim
and before version-row reserve leaves a usable lease for the same version.
No later operation success/failure/cancel/finalize changes the guard. Guard rows
must never be sent to generic operation recovery UX.

Before any version-row reservation, scan the exact Product Job with literal
command prefix `task036.local_transcription` and limit 256. Classify only the
four accepted commands: v1, v2, guard, output slot. Unknown matching commands,
unknown statuses, invalid row coordinates or overflow block both versions.
Output-slot rows are coordination records and are not source operations.
Do not infer source identity by reversing a hashed operation key.

For each opposite-version operation:

- PENDING/null, IN_PROGRESS without a valid v2 admission ref, FAILED without a
  valid v2 admission ref, or PARTIAL without verifiable identity is opaque and
  blocks the entire Product Job conservatively.
- A valid v2 typed admission ref proves only the source SHA, not Asset/Project;
  equal SHA blocks conservatively, including aliases. A different SHA is not a
  source collision, but it does not bypass the shared output-slot check.
- PARTIAL/COMPLETED publication refs require a bounded pinned immutable-set
  read. Verify exact version-specific keys, set/file hashes, operation ID,
  job/command and reconstruct the version operation key from the published
  identity. V2 also validates request -> observation -> decision and historical
  admission freshness. Compare the bound Project/Asset/SHA tuple only after
  validation. Missing or corrupt artifacts remain opaque, never evidence of
  no conflict. Equal source coordinates route only to that version's recovery
  or verification; different verified coordinates do not conflict.
- Merely finding another guard is not proof that an opaque row belongs to it.
  Skip an opposite historical row only when its published/typed identity proves
  it is represented safely; otherwise retain conservative blocking. Guard
  keys themselves contain no recoverable Project/source metadata.

Foreign-set inspection is a read-only structural/hash validator, not recovery:
it cannot promote files, alter rows, create a Provider or adopt foreign settings.
For foreign v1 sets, reconstruct the v1 key using the declared execution-config
SHA after verifying the immutable set; private historic config need not be read.
For exact-operation recovery, additionally recompute config identity from the
current bound settings, as v1 does today.

Two updated processes may scan before either guard exists; uniqueness of
`(job_id, idempotency_key)` and guard CAS still select one version. A historical
v1 PENDING row blocks v2 before v2 reserves its row, and the original v1 retry
can claim the absent v1 lease. No mutual losing PENDING rows are created.

This protocol cannot fence a simultaneously running old binary that does not
implement the guard. R1b proves coordination among updated v1/v2 facades only.
Production activation requires quiescing old Product writers before enabling
v2; it must not claim arbitrary mixed-binary concurrency support. This is a
later activation prerequisite, not a reason to run native processes in R1b.

## 4. Exact generic store API proposal

Keep existing APIs and their semantics. Add an optional constructor keyword
`clock: Callable[[], datetime] | None = None` for the new freshness API only;
default is aware UTC wall time. Existing timestamps and APIs retain their current
`utc_now_iso()` behavior. The v2 facade's probe clock and store clock are separate
injections; tests must demonstrate that stale probe time cannot override store
admission time.

```python
def compare_and_set_operation_status_with_validity(
    self, operation_id: str, *,
    expected_statuses: tuple[str, ...], status: str,
    valid_from: str, valid_until: str,
    expected_result_refs: tuple[str | None, ...],
    result_ref: str | None = None,
    replace_result_ref: bool = False,
    last_error_code: str | None = None,
    increment_attempt: bool = False,
) -> tuple[OperationRecord, bool, str]: ...

def list_operations_by_command_prefix(
    self, job_id: str, *, command_type_prefix: str, limit: int,
) -> tuple[OperationRecord, ...]: ...
```

Fresh CAS validates arguments before mutation, then uses one managed connection
and `BEGIN IMMEDIATE`. Only after acquiring the SQLite write lock does it call
the store clock once. Reject naive/non-UTC/invalid times. Compare the exact
instant to `[valid_from, valid_until)` (strict UTC Z second-precision contract
bounds); return its canonical UTC Z timestamp with microseconds when nonzero.
Do not truncate the clock before comparison. Check status and result-ref in the
same conditional UPDATE, read the row in that transaction, then commit. Return
the row, whether it changed, and the evaluation timestamp. An invalid/stale
window causes no UPDATE and leaves attempt/error/ref/timestamps unchanged.
A missing operation is the existing not-found error. A clock exception rolls
back and performs no admission. No fallback clock, task code, READY policy,
runtime probe or Provider exists in store. The binding checks READY beforehand.

Prefix read validates Job ID, a nonempty UTF-8 prefix of at most 128 characters
without NUL, and integer limit `1..1024` excluding bool. Use bound SQL parameters
and literal prefix comparison (`substr(command_type, 1, length(?)) = ?`), never
unescaped LIKE wildcards. One SELECT orders by operation_id and fetches
`limit + 1`; overflow raises `ERR_STORE_OPERATION_QUERY_LIMIT` without returning
a truncated success. Return all statuses unchanged so the caller can reject
corruption. No state filter, pagination-as-success, or unbounded materialization.

## 5. V2 identity, settings and Provider order

Use the exact R1 section 5 digest domains/keys, and the already accepted R1a
request/observation/decision types. Observation/decision timestamps never enter
the stable operation key. A static settings object is immutable and validates
model, beam integer `1..20` excluding bool, VAD bool, and private cache path.
It has no device/compute/download field. Config construction always sets
`allow_model_download=False`. Normalize only the v2 cache locator with
expanduser, native normalization and non-strict resolution before hashing and
Provider construction; preserve null.

Body-free model identity must be computed without constructing a Provider.
Mirror the existing Provider model-ID rule exactly. To avoid an existing rule
exposing a relative path that matches its slash-bearing model-ID regex, v2
accepts a simple symbolic model name (`[A-Za-z0-9][A-Za-z0-9._-]{0,127}`) or an
absolute platform-local model locator whose Provider ID is hashed. Reject other
relative/slash-bearing locators at settings validation. No existence check,
model file read or model download occurs in R1b. V1 behavior is unchanged.

V2 facade constructor proposal is keyword-only: `settings`, `runtime_request`,
`capability_probe`, `provider_factory`, `clock`, `output_directory`, `store`,
`production_job_id`, optional `language` and `timeline_rate`. Provider factory
signature is `Callable[[FasterWhisperConfig], FasterWhisperProvider]`; it is a
trusted injected dependency, not untrusted script/plugin input. All R1b tests
inject fake model factories and fake capability probes. No default real adapter
is selected by this Unit.

The accepted order is mandatory: static/output checks and v2 identity -> fixed
target preflight -> verified source snapshot -> historical audit -> lease ->
stable operation PENDING -> generation preflight -> fake probe/resolver ->
READY + transactional freshness CAS -> shared slot -> Provider factory ->
Provider validation -> pinned Provider snapshot -> existing transcription service.
There is no Provider factory before operation and slot admission.

Fresh CAS requires `PENDING`, result_ref exactly null, increments attempt once,
sets IN_PROGRESS and typed admission ref. Slot failure may roll back only this
exact IN_PROGRESS/ref to PENDING/null before factory entry. All factory and
later failures retain the admission ref in terminal PARTIAL until a validated
publication ref replaces it. No re-probe after successful admission, even if
the TTL expires during inference.

Add `FasterWhisperProvider.model_loaded` as a read-only bool exposing whether
`_loaded_model` is non-null. Validate returned type, exact provider/model IDs,
full effective config equality, false download and `model_loaded is False`
before transcribe. The trusted factory contract requires fresh construction;
an unloaded object alone is not proof of recent construction. Tests prove
factory invocation/constructor count and reject a preloaded object. Do not
claim this prevents arbitrary side effects inside a malicious factory.

## 6. Publication and Provider-zero recovery

V1 codec remains exact. V2 `publication-set.json` has the v1 identity/file fields,
`publication_set_version=2.0.0`, and exactly these additions:

- `runtime_request`, `runtime_capability_observation`, `runtime_decision`:
  complete typed body-free serialized records;
- `runtime_admission_ref`, `admission_evaluated_at`;
- `task023_config_sha256`, `task023_execution_sha256`;
- `model_download_authorized=false`.

The existing `execution_config_sha256` field carries the v2 static/request
identity. `publication_set_sha256` uses existing canonical-JSON hashing over
the full body without its own digest; version 2 and exact field sets distinguish
it. All additions are covered by that digest. Retain existing 16 KiB set limit
and other file size limits; reject oversized metadata before write. No raw
model/cache path, exception, transcript body or TASK-023 provider payload is
added to the metadata.

Recovery reparses request-bound observation/decision and independently resolves
the observation to compare the complete decision. It recomputes static/request
identity, operation key, typed source/decision ref, full publication digest and
all file identities. It checks freshness at `admission_evaluated_at`, never now.
A TASK-036-local parser accepts only canonical UTC `Z` timestamps in either
`YYYY-MM-DDTHH:MM:SSZ` or `YYYY-MM-DDTHH:MM:SS.ffffffZ` form, with exactly six
fractional digits when present and a nonzero fractional part. It rejects invalid
calendar values, offsets, whitespace, naive timestamps, alternate precision and
`.000000Z` (whose canonical representation omits the fraction). Parse that value
and the decision's existing second-precision bounds as aware UTC datetimes and
compare `issued_at <= admission_evaluated_at < expires_at` without truncation.
The R1a `is_fresh_at` method, schema and serialization remain unchanged; never
pass a fractional admission timestamp into that second-precision API.
TASK-023 config/execution digests are recomputed from the effective config via
an additive pure `build_execution_identity_for_config(config, *, provider_id,
model_id, source_sha256, requested_language)` helper; existing
`build_execution_identity(provider, ...)` delegates with byte-identical output.
No recovery path constructs a Provider merely to obtain diagnostics.

After the immutable set is written, CAS IN_PROGRESS with the exact admission ref
to PARTIAL with publication SHA. Promotion and PARTIAL->COMPLETED reuse the
engine. A crash before that bind leaves the admission ref, even if files happen
to exist: do not infer success or recover from unbound files. A bound publication
is the only roll-forward authority. COMPLETED verifies exact bytes without
Provider re-entry or silently repairing changed fixed output. Finalize validates
Transcript/set/slot identities before release, exactly as legacy does.

The pure recovery classifier receives a validated operation/ref classification
and lease identity; it never performs file I/O. Its caller supplies validated
publication facts from the bounded reader. Exact mappings are:

| V2 operation/ref | Public state | Permitted action |
|---|---|---|
| Absent or PENDING/null | PENDING_ADMISSION | Explicit ordinary admission only. |
| IN_PROGRESS + exact admission ref | ACTIVE_UNKNOWN | No retry/recover; uncertain execution. |
| PARTIAL + validated bound publication SHA | RECOVERABLE_PUBLICATION | Explicit Provider-zero roll-forward. |
| COMPLETED + validated publication SHA | VERIFICATION_ONLY | Exact set verification/redisplay. |
| PARTIAL + exact typed admission ref | ADJUDICATION_REQUIRED_NO_PUBLICATION | No recover; retain slot. |
| FAILED + null satisfying the pre-admission conditions below | FAILED_TERMINAL | No admission/recovery. |
| FAILED + typed admission ref with complete validated source/decision proof below | FAILED_TERMINAL | No admission/recovery. |
| Any other combination, corrupt metadata or required lease mismatch | CORRUPT_BLOCKED | No mutation or recovery. |

FAILED is not produced by R1b's post-admission failure path (which is PARTIAL).
For defensive classification, FAILED/null is permitted only when its exact v2
command, Job, operation key and permanent v2 lease match the requested
Project/Asset/SHA/settings/request identity, `attempt == 0`, and the shared slot
does not name that operation as owner. A null ref with a positive/invalid attempt,
unknown slot ownership or identity mismatch is `CORRUPT_BLOCKED`.

A FAILED typed admission ref is permitted only when `attempt >= 1` is an integer
excluding bool and the caller already has the complete typed request,
observation and decision chain: validate request binding, independently resolve
the observation, compare the complete decision, and require the reference's
source SHA and decision SHA to equal the current exact source and that validated
decision. Also require the exact v2 row/key/lease identity above. A digest-shaped
string alone is insufficient. If this proof is unavailable after restart, return
`CORRUPT_BLOCKED`; do not probe, construct a Provider, discover unbound files or
invent a decision to reconstruct it. This classifier adds no proof store.

A FAILED row with a publication SHA is always `CORRUPT_BLOCKED`, even when an
immutable set happens to validate: the accepted publication lifecycle allows
that ref only under PARTIAL/COMPLETED. Any other FAILED ref/state combination is
also `CORRUPT_BLOCKED`. Every FAILED case, including FAILED_TERMINAL, performs
zero Provider/factory/recovery calls and never releases an uncertain slot.

`RuntimeManagedLocalTranscriptionOutcomeV2` wraps the existing successful
`LocalTranscriptionOutcome` and derives exactly `runtime_request_public` and
`runtime_decision_public` from validated bound objects. Copies cannot be
independently supplied or mutated after construction. Successful execution and
Provider-zero recovery return it; failures remain bounded ProductError codes.
R1c must review how pre-admission errors are presented without inventing a
successful transcript outcome or leaking an exception/digest/path.

## 7. Failure and concurrency matrix

| Failure boundary | Durable outcome | Probe/factory/recovery behavior |
|---|---|---|
| Bad settings/source/output or historical conflict | No requesting version row | No probe/factory. |
| Guard lost/corrupt or scan overflow | No requesting version row | No probe/factory; no lease repair. |
| Generation preflight failure | PENDING/null, permanent same-version lease | No probe/factory; explicit safe retry possible. |
| Probe exception/non-bool/BLOCKED | PENDING/null | No factory; no auto fallback beyond R1a matrix. |
| Before-issued/expiry equality/expired/clock failure | PENDING/null | No factory; attempt unchanged. |
| Same-key admission CAS loser | Existing operation unchanged | Zero factory for loser. |
| Slot busy after successful admission | CAS exact ref to PENDING/null | No factory; lease retained. Failed rollback remains uncertain. |
| Factory/config/preloaded/load/transcribe/lazy iteration failure | PARTIAL + admission ref | No fallback/retry; slot retained for later adjudication. |
| Immutable generation write/bind failure | PARTIAL + admission ref unless set SHA was already durably bound | Unbound files cannot authorize recovery. |
| Fixed promotion/completion CAS failure after set bind | PARTIAL + publication SHA | Provider-zero explicit recovery. |
| Finalize identity mismatch | Existing completed row; slot held | No release or Provider. |
| Crash after guard before operation | Permanent version lease only | Same-version restart may reserve; other version denied. |
| Restart after Provider admission without bound set | IN_PROGRESS or PARTIAL + admission ref | No re-entry; ACTIVE_UNKNOWN or adjudication state. |

Cross-process tests use separate store instances and spawn barriers. Exactly
one same-key admission and at most one opposite-version Provider entry must be
proved through process-shared markers, not a process-local lock. Also exercise
the two same-version/different-config operations sequentially after finalize,
concurrent output-slot contention, opposite-version starts after PARTIAL,
COMPLETED and finalize, and pre-existing v1 PENDING followed by v2 then v1 retry.

## 8. No schema migration proof

Current store has `_SCHEMA_VERSION=3` (`store.py:25`), migration records `(1,2,3)`
(`:549-559`, `:609`) and existing operation columns:
`operation_id`, `job_id`, `command_type`, `idempotency_key`, `status`, `attempt`,
`created_at`, `updated_at`, `last_error_code`, `result_ref`. Existing uniqueness
is `(job_id, idempotency_key)` (`:483-492`). Current generic CAS accepts exactly
PENDING/IN_PROGRESS/PARTIAL/COMPLETED/FAILED and refs up to 2048 UTF-8 characters;
the proposed refs fit those bounds. Guard and v2 rows need no new storage shape.

Do not change `_initialize`, either migration, SQLite DDL/indexes, schema version,
or `_validate_existing_database`. Tests compare schema fingerprint, operations
column order/types, sqlite_master, migration rows and `PRAGMA user_version`
before/after. The application schema version is not SQLite user_version: no
source currently sets that pragma, so assert preservation (a newly created
fixture is expected to remain 0), not a fabricated user_version 3 migration.
Reopen via `require_existing=True` to exercise current pinned DB validation.

## 9. Proposed exact implementation files

This list is a proposal for later acceptance, not permission to start mutation.

- `src/ai_video_production/task036_product_ports.py`
- `src/ai_video_production/store.py`
- `src/ai_video_production/faster_whisper_asr.py`
- `src/ai_video_production/faster_whisper_reconciliation.py`
- `tests/test_task098_task036_runtime_managed_transcription.py`
- `tests/test_task036_local_transcription_operation.py`
- `tests/test_task023_faster_whisper_reconciliation.py`
- `tests/test_idempotency.py`
- `docs/ai-team/current-state.md`
- `docs/ai-team/task-index.md`
- `docs/ai-team/tasks/TASK-098/task.md`
- `docs/ai-team/tasks/TASK-098/a2-r1-runtime-integration-design-20260919.md`
- `docs/ai-team/tasks/TASK-098/a2-r1b-pre-mutation-review-20260919.md`
- `docs/ai-team/tasks/TASK-098/evidence/a2-r1b-runtime-managed-transcription-20260919-r01.md`

No runtime contract/schema, launcher/UI, other Task history, OS repo, dependency
lockfile or DB artifact is allowed. If implementation requires another file or
an incompatible contract choice, stop that mutation and bring the exact delta
back to review; do not expand scope through imports or generated fixtures.

## 10. Acceptance and review gates

| Test owner/file | Required evidence |
|---|---|
| R1b new test | Exact stable v2 digests and all runtime request variants; no observation/time in key; settings/privacy validation; every failure/classifier row; complete chain tamper/unknown/foreign rejection; historical freshness including a valid fractional admission, one microsecond before expiry, expiry equality and noncanonical timestamp rejection; every FAILED/null/typed/publication/malformed case and missing/source-mismatched/decision-mismatched proof; Provider-zero recovery and zero calls for all FAILED cases; all false download/real-effect invariants. |
| TASK-036 existing test | Existing suite unchanged in meaning; independent v1 golden key/config/publication bytes; legacy recovery/finalize; new symmetric lease tests including cross-process starts, every opposite state, same-version config changes and crash windows. |
| TASK-023 test | Existing byte identity preserved; config-only and Provider routes match; loaded-state observation is read-only/model-free; private path absence in v2 publication/outcome. |
| Idempotency test | Fresh CAS exact timestamp after write-lock acquisition; issued equality/expiry equality/fractional expiry; result-ref-null and attempt semantics; thread/process CAS; literal prefix/all statuses/bounds/overflow; DB shape/user_version unchanged and existing DB reopens. |

Direct regression includes existing R1a/A2-R0 contracts and TASK-006/023/036
focused suites. Preserve existing test meaning and assertions; add only new
boundary tests in the exact allowed test files, not mechanical assertions
mirroring helpers. Fake providers operate on synthetic
tmp_path bytes only. No CTranslate2 import or real model factory is reached.

Independent Critic and Tester must close all Critical/High findings; independent
Judge must accept this allocation before Product mutation. Implementation then
requires focused tests, boundary/regression results, Critic, Tester, final Judge,
diff/Allowed Files audit and durable Evidence/read-back before commit-ready.
Architecture/state-machine/final review use High-Reasoning; implementation uses
Implementation capability; fixture/doc synchronization uses Bulk/Mechanical.

Test roots must be OS-allocated unique temp paths or the exact Task worktree;
no drive-root/direct-child artifact. External checkpoint uses
`C:\home\baisound\evidence\bai-video-production\TASK-098\a2-r1b-runtime-managed-transcription\<run-id>\`.
The eventual checkpoint records the resolved actual run roots, hashes, HEAD,
dirty ownership, test results and intentional residuals, then reads them back.

## 11. Gates, exclusions and review decisions still needed

This review executes no tests or native processes and grants no implementation
authority. Product source/tests are unchanged. R1c launch/bridge/UI is excluded.
A2-R2 progress, cancellation, Human adjudication and safe uncertain-slot release
are excluded and mandatory before real v2 activation. Real OS/GPU/DLL capability,
model inference/download, private audio, training, packaging/install/launch,
Release/Deploy/Production and external accounts remain explicit later gates.

Independent review must specifically accept the following refinements before
allocation: exact generic store signatures/clock precision, conservative
unprovable historical-row handling, v2 relative-model-locator rejection,
config-only TASK-023 diagnostic helper, successful-outcome/error distinction,
and old-binary quiescence as an activation prerequisite. These are proposed
bounded resolutions, not claims of already accepted behavior.

Technical implementation result: `NOT_CONFIRMED / NOT_EXECUTED`.
Design result: `ACCEPTED / IMPLEMENTATION_ALLOCATED`.

## 12. Review outcome

- Independent Architect: bounded current-source review completed.
- Independent Critic: first `0 Critical / 0 High / 2 Medium / 0 Low`, final
  `0 Critical / 0 High / 0 Medium / 0 Low / ACCEPT`.
- Independent Tester: first `0/0/1/0`, final `0/0/0/0 / PASS`.
- Independent Judge: `ACCEPT / A2-R1b implementation allocated / 0/0/0/0`.
- Product source/test/native/provider/model/private/training effects:
  `NOT_EXECUTED`.
- Next action: implement only the exact file set in section 9, then satisfy the
  section 10 tests and independent completion reviews.
