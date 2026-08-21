# TASK-054 R3B Route Capability Design

Date: 2026-08-22

Status: `BOUND_FOR_IMPLEMENTATION`

Development depth: `DEV-3 HIGH ASSURANCE`

## Goal

Resolve one configured Provider-neutral route for an already current R3A DbD
tuned-model binding and produce an immutable, body-free capability decision.
R3B does not call a Provider, load a model or adapter, resolve credential values,
or authorize Product execution.

## Canonical ownership

- `TunedModelBinding` remains the binding body/checksum owner.
- `DbDTunedModelRegistry` remains lifecycle/latest/revocation owner.
- `AiConnectionProfile` remains configured route/profile owner.
- `AiConnectionResolver` remains the only Provider route selector.
- R3B owns only the exact binding-to-route capability decision.
- R3C may consume the decision in a deterministic fake adapter test boundary.
- R3D remains the separately gated canonical Provider/local adapter integration.

No second Provider stack, credential store, binding registry, Candidate Store,
route selector or execution-authority system is introduced.

## Resolution contract

The pure resolver accepts an admitted `DbDTunedModelRegistry`, an admitted
`AiConnectionProfile`, `ConnectionAvailability`, locale/schema coordinates and
an optional explicit binding ID.

1. Resolve exactly one latest APPROVED R3A binding.
2. Require the binding route capability
   `DBD_TUNED_COMMENTARY_REASONING` and exact Context/Output schema versions.
3. Call `AiConnectionResolver.resolve` for `AiWorkload.PLANNING` with that exact
   required capability.
4. Require the selected route settings to pin the resolved binding with:
   `dbd_tuned_binding_id`, `dbd_tuned_binding_revision`, and
   `dbd_tuned_binding_sha256`.
5. Emit an exact-admitted `DbDReasoningRouteDecision`.

The pin prevents a generic capable route or a stale approved binding revision
from being silently selected. Runtime artifact loading/digest verification is
not claimed here and remains R3D responsibility.

## Decision boundary

The decision contains only:

- binding and R3A registry-record identities;
- connection profile identity/checksum;
- selected route/provider/model/cost/reasoning-effort coordinates;
- boolean credential/endpoint configuration indicators;
- the fixed route capability;
- `execution_authority_state=NOT_AUTHORIZED_R3D_REQUIRED`;
- a canonical checksum.

It never contains a credential reference/value, endpoint reference/value,
route settings, prompt, output body, raw Provider response, Dataset body or
Human PII. A decision/checksum is Evidence, not an authentication token.
Every later consumer must call `validate_current`, which exact-admits the record,
reruns canonical Registry/Profile/availability resolution and rejects any stale
or rehashed coordinate before use.

## Fail-closed rules

- disabled/unavailable/missing-capability routes retain existing resolver errors;
- absent, stale or mismatched route binding pins are data-integrity failures;
- ambiguous approved bindings require explicit binding selection;
- suspended/revoked/rejected bindings cannot resolve;
- unknown schema, record kind, field, enum or checksum is rejected;
- fallback is not implemented and cannot be silent;
- paid/free/local route selection is visible but never executable in R3B.

## Allowed files

- `src/ai_video_production/dbd_reasoning_routing.py`
- canonical route-decision schema and exact resource mirror
- `tests/test_task054_dbd_reasoning_routing.py`
- this design and bounded TASK-054 current-state summaries at completion

Must not modify Provider adapters, `AiConnectionResolver`, credential stores,
model/runtime/Dataset/training/TTS/Timeline/Candidate/Human-review code,
workflow, release or deployment files.

## Acceptance

- deterministic route selection uses the existing resolver;
- exact binding pin, profile hash and registry record are retained;
- missing/stale/crossed/rehashed coordinates fail closed;
- route ambiguity, revocation and required-capability failures are covered;
- runtime and JSON Schema admission are exact and mirrors are byte-identical;
- no Provider/model/runtime/credential/I/O side effect exists;
- R3A/TASK-028 and TASK-054 direct regressions pass;
- independent Critic/Judge has unresolved Critical/High `0 / 0`.
