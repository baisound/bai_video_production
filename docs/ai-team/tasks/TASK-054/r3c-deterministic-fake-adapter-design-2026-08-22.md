# TASK-054 R3C Deterministic Fake Adapter Design

Date: 2026-08-22

Status: `BOUND_FOR_IMPLEMENTATION`

Development depth: `DEV-3 HIGH ASSURANCE`

## Goal

Provide a deterministic, test-only, in-memory adapter harness for exercising the
R3B current-route boundary and R2A strict parser under success and bounded fault
conditions. R3C never invokes a Provider, resolves credentials, loads a model or
adapter, persists output, or grants execution authority.

## Canonical ownership

- R3A remains binding lifecycle/latest/revocation owner.
- R3B remains current binding/profile/route capability owner.
- `DbDReasoningProposalParser` remains raw-output structural admission owner.
- R2B/R2C/R2D remain Fact/Policy/Candidate/Human-lineage owners.
- `DbDReasoningExecutionReceipt` remains the future R3D attempt Evidence owner.
- R3C owns only deterministic fake emission and body-free fault-test results.

The fake adapter is not a Provider adapter and cannot be registered in the
canonical Provider stack.

## Test-only invocation

`DbDReasoningFakeInvocation` carries an attempt ID, exact R3B decision,
Context/prompt-template/output-schema digests and a fixed
`TEST_ONLY_NO_PROVIDER_EXECUTION` state.

Before every emission the harness calls R3B `validate_current` with trusted
Registry/Profile/availability inputs. A route-decision checksum is never accepted
as authority. Binding revocation, profile drift, availability drift or route pin
drift fails before fake emission.

## Deterministic scenarios

One explicit frozen scenario is supplied per invocation:

- `SUCCESS`: one bounded raw UTF-8 JSON fixture is parsed by R2A;
- `MALFORMED_OUTPUT`: one bounded/oversized invalid fixture is passed to R2A;
- `TIMEOUT`, `CANCELLED`, `RUNTIME_UNAVAILABLE`, `RESOURCE_LIMIT`: no raw output
  exists and one stable fault code is returned.

The scenario is an in-memory test fixture, not a canonical or persisted record.
It has no retry loop, random source, clock, network, file, process or Store access.

## Non-retention result

The public `DbDReasoningFakeAttempt` contains only:

- attempt/scenario/outcome and stable error code;
- route-decision, Context, prompt-template, output-schema and raw-output digests;
- deterministic elapsed/token counters;
- the R2A `StructuralParseResult` when raw output existed;
- `TEST_ONLY_NO_PROVIDER_EXECUTION`.

The raw fixture exists only in the private emission while the parser runs and is
not retained on the returned Attempt. The result creates no ExecutionReceipt,
Proposal, Candidate, review, Dataset or training record.

## Fail-closed rules

- forged/stale R3B decisions fail before invocation;
- SUCCESS requires raw bytes and no fault code;
- non-output faults forbid raw bytes and parsing;
- MALFORMED_OUTPUT requires raw bytes and a failed parser result;
- result coordinates and parser raw digest must match exactly;
- bool-as-int, negative metrics, unknown outcome/state and inconsistent fault
  combinations are rejected;
- no automatic fallback or retry exists.

## Allowed files

- `src/ai_video_production/dbd_reasoning_fake_adapter.py`
- `tests/test_task054_dbd_reasoning_fake_adapter.py`
- this design and bounded TASK-054 current-state summaries at completion

Must not modify R3A/R3B canonical modules, Provider adapters/resolver,
credential stores, model/runtime/Dataset/training/TTS/Timeline/Candidate/Human
review code, schemas, workflow, release or deployment files.

## Acceptance

- deterministic success reaches the existing R2A quarantine only;
- every fault produces stable body-free output and no raw retention;
- current-route/revocation/profile/availability crossing fails before emission;
- malformed/duplicate/oversized raw fixtures retain R2A fail-closed behavior;
- no I/O, Provider, credential, model/runtime, Store or training surface exists;
- focused and direct R3A/R3B/R2A regressions pass;
- independent Critic/Judge has unresolved Critical/High `0 / 0`.
