# TASK-098 A2-R2c Design Allocation Evidence

## Identity

- Project / Task / Unit: `BAI VIDEO PRODUCTION / TASK-098 / A2-R2c`.
- Base HEAD: `01de550f665a000cf70b8cbfb38556fc517020f8`.
- Branch: `codex/task-098-universal-wav-review-integration`.
- Governance: `DEV-3 HIGH ASSURANCE`.
- Effect level: documentation-only design review.

## Outcome

- Independent Critic: initial `REJECT / 0/3/1/0`; final
  `ACCEPT / 0/0/0/0`.
- Independent Tester: initial `FAIL / 0/2/2/0`; final
  `PASS / 0/0/0/0`; dynamic execution `NOT_CONFIRMED` for design review.
- Independent Judge: `ACCEPT / IMPLEMENTATION_ALLOCATED / 0/0/0/0`.

Closed corrections include the state-specific presence matrix, canonical
TASK-036 recovery-classifier input, full server-only durable snapshot, exact
invocation-epoch phase/worker binding, deterministic monotonic expiry, all
twenty reducer-row goldens, concurrent/foreign confirmation rejection and the
non-shadowing R1c/R2c route table.

## Exact allocation

Source:

1. `src/ai_video_production/task098_runtime_transcription_coordination.py`
2. `src/ai_video_production/task036_product_ports.py`
3. `src/ai_video_production/task036_pre_edit_runtime.py`
4. `src/ai_video_production/task036_shell_ui.py`

Tests:

5. `tests/test_task098_runtime_transcription_coordination.py`
6. `tests/test_task098_task036_runtime_managed_transcription.py`
7. `tests/test_task036_pre_edit_runtime.py`
8. `tests/test_task036_shell_ui.py`
9. `tests/test_task036_trusted_launcher.py`

Bounded TASK-098/current-state/task-index documentation is also allocated.
Store/schema/reducer, Provider, launcher/CLI/first-run, packaged/native Shell,
serialized v2 activation and all other source/test files are read-only.

## Gates

Implementation must satisfy the accepted section 7 matrix, independent DEV-3
implementation review, maximum two bounded fix cycles, exact scope/diff check,
and durable external Evidence read-back. No real Provider/model/private media,
voice learning, installation, Release, Deploy or Production effect is allowed.
