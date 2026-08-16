# TASK-020 Resource Admission / Monitoring Foundation R0

Date: 2026-08-17
Authority: `BVP-AUTH-20260817-TASK020-RESOURCE-ADMISSION-MONITORING-FOUNDATION-R0-01`
Implementation base: `404149a1c8d9bb722f9bdaa2ce7ba9d8ee7a23cf`
Runtime/effect authority: **not granted**

## Outcome

This unit defines a body-free, provider-neutral contract for resource preflight, admission decisions, bounded runtime watermark Evidence, incident Evidence and operation-gate bindings. The implementation only parses, hashes, validates, evaluates and projects caller-supplied metadata. It does not collect host data, reserve a GPU, schedule work, launch or terminate processes, contact the network or authorize execution.

`CANONICAL_REF_NOT_PROVIDED`, missing required facts, unsupported facts, stale facts, mixed probe profiles and unknown observations fail closed. A successful decision reaches only `READY_FOR_EXTERNAL_HUMAN_GATE`; `execution_authorized` remains false.

## Existing truth and non-duplication

| Owner | Hosted responsibility | TASK-020 use | Not duplicated |
|---|---|---|---|
| TASK-004 | ComfyUI stats, GPU visibility, VRAM/RAM/disk floors | External observations may become metric facts | client, stats parsing, disk query, dispatch |
| TASK-014 | narration engine/model/runtime/license/right/resource bindings | exact decision/profile hashes may be referenced | VoiceProfile, Consent, load or render |
| TASK-043 | durable job state, recovery and persistence | later job owners may bind admitted operations | job/store/queue or `PROJECT_MAINTENANCE` reuse |
| TASK-046 | recording-session resource binding and authorization boundary | consumes a canonical TASK-020 decision | capture command, OBS dispatch, state machine |
| TASK-047 | OBS plug-in/controller and runtime acceptance | external process/app counts may be supplied | plug-in load, launch, capture, process control |
| TASK-048 | acoustic calibration and quality policy | independent exact reference only | analyzer, audio access, quality decision |

Only repository serialization helpers are imported. Existing owners are unchanged.

## Canonical graph

1. `ResourceMetricFact` (nested canonical type): closed kind/state enums, integer truth, exact unit/time/source profile and deterministic hash. Genuine measured zero is distinct from unknown null.
2. `ResourceAdmissionPolicyRevision`: immutable revision/parent, sorted unique integer thresholds, fact age policy and exact successor validation.
3. `ResourcePreflightObservationReceipt`: exact operation/target/policy binding and sorted facts; collector/operation effects false.
4. `ResourceAdmissionDecisionReceipt`: `ADMITTED | DENIED | UNKNOWN`; deterministic reasons; reservation/dispatch/authorization false.
5. `RuntimeResourceWatermarkReceipt`: exact admitted-decision lineage, sequence/window and `WITHIN_ADMITTED_BOUNDS | BREACH | UNKNOWN`; collection/process/app effects false.
6. `ResourceIncidentReceipt`: additive Evidence from a non-healthy watermark; termination/kill/app-stop effects false.
7. `ResourceOperationGateBinding`: structured unresolved/mismatch/unknown handling; verified admission yields a Human-Gate candidate, never execution authority.

The public schema is mirrored byte-for-byte under `schema_resources`. Unknown root types, properties and enum values are rejected.

## Decision rules

- Required missing or non-measured fact: `UNKNOWN`, never zero.
- Stale/future fact or mixed source profiles: `UNKNOWN`.
- Exact threshold failure: `DENIED` at preflight, `BREACH` at runtime.
- A threshold failure dominates concurrent unknown reasons; admission cannot become unsafe PASS.
- Policy successor requires same identity, revision +1, exact parent hash and advancing time.
- An unresolved Gate contains no invented decision reference/hash.
- No automatic retry, reservation, dispatch, process/app start, stop or kill exists.

## Projection and privacy

Private projection retains opaque target, input/source bindings and measured integers for authorized consumers. Public projection removes target/source references, source-profile hashes, target/input digests and exact metric values. Absolute paths, traversal and credential-like identity values are rejected.

## Pure API / absent effects

Pure API: canonical dataclasses/enums, `parse_resource_record`, `canonical_record_digest`, `validate_policy_successor`, `evaluate_admission`, `classify_runtime_watermark`, `derive_incident`, `classify_operation_gate`, projections and `module_effect_surface`.

Absent: OS collector, filesystem/network probe, process enumerator, reservation/scheduler, queue/job/store, app launcher, signal/kill API, provider adapter and media/audio/model operation.

## Synthetic acceptance inventory

| Case | Expected |
|---|---|
| measured zero / unknown null / unknown zero | preserved / preserved / rejected |
| wrong unit, invalid network value, hash tamper | rejected |
| bad revision parent/gap/fork/time | rejected |
| unsorted/duplicate thresholds or facts | rejected |
| all required thresholds pass | `ADMITTED` |
| measured threshold failure | `DENIED` |
| missing/unsupported/stale/mixed profile | `UNKNOWN` |
| mismatched project/policy/revision | rejected |
| runtime threshold failure | `BREACH` plus additive incident Evidence |
| healthy watermark incident | rejected |
| unbound Gate | `UNKNOWN` |
| verified admitted Gate | Human-Gate candidate; every effect false |
| forged authorization/reservation/process/app effect | rejected |
| unknown type/extra property/path | rejected |
| public projection | exact values/private refs suppressed |
| schema mirror/static effect scan | byte exact / no effect surface |

## Validation Evidence

- Focused TASK-020 tests: **15 passed**.
- Windows full regression: **1472 passed, 1 platform skip**.
- WSL2 Ubuntu full regression: **1472 passed, 1 platform skip**.
- Windows compile: **PASS**.
- Schema/mirror bytes and Draft 2020-12 validation: **PASS**.
- Audio/media/model/provider/filesystem-store/process/app/network/reservation effects: **0**.

## Critic 1 — Builder/domain

Reviewed hashes, revision lineage, integer comparisons, stale handling, deterministic reasons, operation identity and admission/watermark/incident/Gate separation. Corrections: exact successor validation, pure runtime classification/incident derivation and parsed UTC window ordering.

Residual Critical/High/Medium: **0 / 0 / 0**.

## Critic 2 — Security/privacy

Reviewed forged booleans, path/credential/body leakage, unknown-to-zero conversion, projection and external-owner boundaries. Corrections: public values/source hashes suppressed; path/traversal/private terms rejected; collector/reservation/dispatch/process/app flags fixed false in schema and runtime.

Residual Critical/High/Medium: **0 / 0 / 0**.

## Critic 3 — Compatibility/integration

Reviewed hosted TASK-004/014/043/046/047/048 fragments. TASK-020 consumes only body-free references and renames no API. Exact five paths overlap neither active P-VS-3B nor PR #142. PR #142's ComfyUI change is an incoming dependency fragment; if merged first, the authorized zero-overlap normal-merge/read-back procedure applies.

Residual Critical/High/Medium: **0 / 0 / 0**.

## Judge

- Domain/pure metadata contract: **PASS**.
- Focused and Windows/WSL regression: **PASS**.
- Schema/runtime/mirror parity: **PASS**.
- Existing-owner duplication / forbidden effects: **0 / 0**.
- Collection/reservation/process/app execution: **NOT AUTHORIZED / NOT IMPLEMENTED**.
- `BVP-ILOCK-20260817-TASK020-R0-CHANGELOG-01`: **RESERVED_NOT_ACTIVE** until PR #142 releases the shared lane.
- Residual Critical/High/Medium: **0 / 0 / 0**.
