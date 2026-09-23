# TASK-098 A2-R2b2 Design Allocation Evidence

- Project / Task / Unit: `BAI VIDEO PRODUCTION / TASK-098 / A2-R2b2 design`.
- Pre-commit HEAD: `19a03783f97509af602e881b5a447398762a1032`.
- Branch: `codex/task-098-universal-wav-review-integration`.
- Base/current local main: `28ba61e5f01047a716c681a3584be22500fe53fc`.
- Governance: `DEV-3 HIGH ASSURANCE`.
- Critic: `ACCEPT / 0/0/0/0`.
- Tester: `PASS / 0/0/0/0`.
- Judge: `ACCEPT / R2b2 LIMITED IMPLEMENTATION ALLOCATED / 0/0/0/0`.

## Accepted boundary

- Exact source ceiling: R2b1 coordinator, TASK-023 FasterWhisper concrete
  Provider/service and TASK-036 Product port/engine only.
- Exact test ceiling: TASK-006 FasterWhisper, TASK-036 v1 lifecycle, R2b1
  coordinator and TASK-098/TASK-036 v2 integration tests only.
- Legacy `transcribe(request)`, v1 operation identity and publication bytes stay
  unchanged. Cooperative iteration is a separate fake-only v2 path.
- V2 creates no operation generation child before publication wins. Confirmed
  cancel paths bypass generic PARTIAL handling; unconfirmed iterator close keeps
  the exact admission and slot. Publication binds main before control and
  Provider-zero recovery reconciles control before fixed promotion.
- Barrier-only or immutable-before-main crash states are blocked/no-replay.
- No store/schema/Shell/launcher/CLI/native/private/real Provider/model/training,
  serialized activation, release, deploy or Production effect is allocated.

## Next action

Implement one R2b2 Atomic Unit inside the accepted seven-file ceiling, execute
the deterministic fake race/crash/close matrix and direct dependency regression,
complete independent implementation review, and persist/read back external
Evidence before commit. R2c remains unallocated.
