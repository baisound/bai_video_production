# TASK-043 P-FND-4 Durable Product Job — Implementation and Critic Evidence

- Date: `2026-08-15`
- Base: `main@19febe3e00de92b18948e93740a0e3080b63d1b1`
- Branch: `refactor/task-043-durable-product-jobs`
- Authority: `AUTONOMY_MAJOR_REFACTOR_CONTINUOUS_RELEASE`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`

## Implemented contract

- closed public/package `durable-product-job.schema.json`;
- Project-scoped checksummed `.bai-project/jobs.json` with atomic write and
  Project lock serialization;
- deterministic `(kind, target, exact input hashes)` operation identity and
  idempotent enqueue;
- bounded CAS state machine through preflight, dispatch, running, terminal,
  UNKNOWN and HUMAN_REQUIRED states;
- restart conversion from DISPATCHING/RUNNING to UNKNOWN without replay;
- typed UNKNOWN/Human reconciliation actions and immutable attempt count;
- nullable estimated/actual cost truth with explicit currency/source when known;
- allowlisted Product-local Export/analysis/transcode/index/maintenance kinds;
- read-only TASK-036 `JobSnapshot` projection and explicit Shell command authority
  for `job.enqueue`, `job.cancel` and `job.reconcile`.

## Ownership and authority

The durable store supports TASK-044 background/Export work. It explicitly does
not replace TASK-027 Generation Queue or Provider Attempt Evidence. A Job record
does not authorize Provider, paid, credential or external execution. The Shell
still requires its normal command/context/confirmation authority before an
executor can perform an external operation.

## Critic review and corrections

1. `HIGH / CLOSED` — A valid `jobs.json` copied from another Project could have
   passed a transition. Every mutating/recovery service call now rechecks store
   Project identity against the current Manifest under the Project lock.
2. `HIGH / CLOSED` — An open `kind` could duplicate TASK-027 Provider Generation
   Queue. Kinds are now restricted to Product-local work; Provider generation is
   rejected by the model and schema.
3. `HIGH / CLOSED` — UNKNOWN could be mistaken for retryable work. UNKNOWN has no
   transition to READY/DISPATCHING. Completion/failure/Human routing requires the
   exact typed recovery action; restart recovery is idempotent.
4. `HIGH / CLOSED` — Shell visibility alone could be mistaken for capability.
   enqueue/cancel are LOCAL_DURABLE, reconcile is HUMAN_FINAL_AUTHORITY, and the
   projection itself performs no mutation.
5. `MEDIUM / CLOSED` — Unknown cost could be serialized as zero. Null remains
   unknown; a numeric cost requires explicit ISO currency and estimated cost also
   requires an estimate source.
6. `MEDIUM / CLOSED` — Host paths or private identifiers could leak into public
   target/result fields. Drive/absolute/traversal/private-term identities are
   rejected; records contain hashes/references rather than payloads.

Final unresolved Critical/High: `0 / 0`.

## Allowed Files expansion

The authorized design already requires a Shell projection but its candidate file
list named only `durable_product_job*.py`. The bounded implementation necessarily
adds only the three declared command specifications to
`src/ai_video_production/desktop_shell.py` and a matching authority test in
`tests/test_task036_desktop_shell.py`. No executor, UI, Provider adapter or
external mutation path is added.

## Validation

- `python -m compileall -q src tests`: PASS
- P-FND-4/TASK-043/Shell focused: `90 passed`
- full Windows Python 3.12 regression: `1061 passed, 1 skipped`
- public/package schema bytes and representative instance validation: PASS
- `git diff --check`: required before commit

The skip is the existing TASK-034 non-Windows credential-vault contract.

## Next gate

Hosted CI and exact main merge/cleanup are required. This final foundation unit
does not justify a standalone release. After hosted closure, re-audit TASK-042
P-V6-4 Timeline Audio implementation against the accepted TASK-043 contracts.
