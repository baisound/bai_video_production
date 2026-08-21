# TASK-054 R3A Binding Registry Design

Date: 2026-08-22

Status: `BOUND_FOR_IMPLEMENTATION`

Development depth: `DEV-3 HIGH ASSURANCE`

## Goal

Add the provider-neutral registry lifecycle and revocation boundary for DbD tuned
reasoning bindings. R3A does not execute a Provider, activate a route, download a
model or adapter, approve a binding, or create Human authority.

## Canonical ownership

- `TunedModelBinding` remains the only binding body and checksum owner.
- `DbDTunedModelRegistryRecord` owns append-only lifecycle lineage only.
- `DbDTunedModelRegistry` is a pure immutable aggregate over admitted records.
- R3B remains the owner of route capability and execution authorization.
- Existing `AiConnectionResolver` remains the canonical Provider route selector.

No second model body, credential store, Candidate Store, Provider stack, or
approval authority is introduced.

## Lifecycle

Each `binding_id` has an independent, gap-free revision chain:

```text
DRAFT -> EVALUATED -> APPROVED -> SUSPENDED -> APPROVED
                   \-> REJECTED               \-> REVOKED
```

Every transition creates a new immutable `TunedModelBinding` revision and a new
registry record. In-place status mutation, revision gaps, forks, replay, direct
APPROVED-to-REVOKED transitions, and return from REVOKED or REJECTED are rejected.

The first record must be revision 1 / DRAFT / REGISTER. Later records must point
to the exact previous record checksum. Base model, adapter, locale and schema
coordinates cannot change inside one binding chain. Dataset, recipe, evaluation
and rights digests may be completed only by the DRAFT-to-EVALUATED transition and
are immutable afterwards.

## Authority boundary

Human-sensitive transitions carry a body-free positive-grammar
`human-confirmation://<Crockford-ULID>` Evidence reference and its digest.
Technical registration/evaluation transitions carry a body-free
`registry-intake://sha256/<hex>` or `evaluation://sha256/<hex>` reference.

These references and hashes are audit Evidence, not authentication tokens.
Registry records always serialize
`execution_authority_state=NOT_AUTHORIZED_R3B_REQUIRED`. R3A resolution never
returns Provider, model-download, training, activation, or dispatch authority.

## Resolution

Resolution considers only the latest record of each binding chain. A latest
APPROVED binding may be selected only when locale and the current Context/Output
schema versions match. SUSPENDED, REVOKED, REJECTED, DRAFT and EVALUATED latest
records never resolve. An unspecified binding ID must yield exactly one eligible
binding; ambiguity fails closed. There is no silent fallback to an older approved
revision or another binding.

## Context scope

May modify:

- `src/ai_video_production/dbd_tuned_model_registry.py`
- `schemas/dbd-tuned-model-registry.schema.json`
- exact schema resource mirror
- `tests/test_task054_dbd_tuned_model_registry.py`
- this design and bounded TASK-054 current-state summaries at completion

Must not modify:

- Provider adapters or `AiConnectionResolver`
- model/runtime/Dataset/training/TTS/Timeline code
- Candidate/Human review stores
- release/deploy/workflow files

## Acceptance

- exact runtime/schema admission and byte-identical schema mirror;
- gap/fork/replay/cross-binding/artifact drift fail closed;
- suspension/revocation immediately remove latest resolution eligibility;
- no rollback to an older approved revision;
- ambiguous locale resolution fails closed;
- no filesystem, SQLite, network, subprocess, Provider or credential effects;
- R0-R2 and direct TASK-049 regression remain green;
- unresolved Critical/High findings are zero.
