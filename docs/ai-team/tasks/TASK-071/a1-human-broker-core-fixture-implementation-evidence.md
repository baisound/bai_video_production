# TASK-071-A Human Broker Core Fixture V1 — Implementation Evidence

## Binding

- Base: `origin/main` / `b7b2f33f9acca95b5bf0d727361f0e794a2d5f82`
- Branch: `codex/task-071-a-human-broker-core-fixture-v1`
- Worktree: dedicated, clean before this Atomic Unit
- Development depth: DEV-4, effect-zero fixture contract only

## Delivered boundary

The public module exposes only the four closed V1 action names, immutable audit
projections, a bounded strict JSON decoder, and an effect-zero chain projection.
It does not create a Human authority, ticket, capability, native UI/process,
durable state, provider call, or external effect.

All three schema families require `authority_created=false`,
`effect_performed=false`, and `native_user_presence_verified=false`.
Root and packaged-resource schema bytes match:

- reservation: `141880AD3FCDAA4BEBDC0C775BB7F8656601C3946F189B46209943BC0A5F0AA9`
- decision event: `DA39B152D08812E32DCA0DF7AD97249643BA177BC0CC4AB6B09AD76138157D2F`
- audit receipt: `B6439F503A0ACA6303F30AB190ACCD3F5799C3C65EACE68B9BE0DF8E82DDBEC9`

## Verification

Executed from this dedicated worktree using the pre-existing Task-077 Python
environment, without bytecode or pytest-cache writes:

```text
python -B -m pytest -p no:cacheprovider -q tests/test_task071_human_authorization.py
24 passed
```

The focused coverage includes Draft 2020-12 schema checks, mirror equality,
duplicate keys, NaN/Infinity/overflow float, BOM, trailing bytes, invalid UTF-8
control characters and escaped lone UTF-16 surrogates in values or keys; copy/pickle/reconstruction; exact canonical digest
binding; unknown and cross-action rejection; replay/expiry rejection;
128-thread audit projection stability; and effect-flag rejection.

`git diff --check` passed. Native broker, Windows user presence, durable
one-use consume, and real Human authorization are not implemented or executed;
they remain outside this fixture Atomic Unit.
