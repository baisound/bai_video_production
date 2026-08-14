# TASK-013 — R4 Safe Runtime Launch-Flag Hardening Design / Review / Authorization

- Date: `2026-08-14`
- Owner route: continue BAI VIDEO PRODUCTION under BAI Development OS governance
- BAI Development OS queue result: `TASK-013-SAFE-RUNTIME-HARDENING / IMPLEMENTATION`
- Parked unit: `TASK-013-NATIVE-H3-GATE / HG-BVP-TASK013-NATIVE-003`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`
- Scope: incident-derived pre-dispatch runtime-argument hardening only

## Current OS audit

The implementation Source of Truth is current BAI VIDEO PRODUCTION main
`21228d15e207fb76c5367c28968430789f682885`. BAI Development OS v1.1.0 is
external development governance and is not a Product runtime dependency.

TASK-013's bounded local Comfy adapter is hosted-closed, but native H3
completion remains `PARKED_TO_SAFE_RUNTIME_REVIEW`. Attempt 02 used
`--disable-dynamic-vram`, `--disable-async-offload`,
`--disable-pinned-memory` and `--lowvram` before an Owner-confirmed Windows
force restart. The Product currently rejects the first and fourth flags, but
does not reject the two remaining incident flags when they appear alone. The
current exact-token comparison also does not classify `--flag=value` variants.

## Registry and DEV Profile decision

This is an existing TASK-013 corrective unit, not a new Product Task. It owns a
pre-side-effect safety boundary in a native external runtime, preserves an
uncertain prior side effect and can affect whether a generation dispatch is
allowed. DEV-4 remains required.

BAI Development OS Autonomous Queue parks the native run behind
`NATIVE_EXTERNAL_APPLICATION` while allowing this independent repository-only
hardening. No Human Gate is satisfied or bypassed by this unit.

## Allowed files

- `src/ai_video_production/local_comfy_generation_port.py`
- `tests/test_task013_local_comfy_generation_port.py`
- `PROJECT.md`
- `docs/ai-team/project-summary.md`
- this design/review/authorization record
- the paired local closure Evidence
- current Product state, Task index and canonical roadmap status lines

Raw `evidence/native/**`, private Prompt content, runtime journals, launch
configuration, generated media and operator workflows are outside Allowed Files.

## Builder design

1. Define one canonical set of prohibited native runtime flags.
2. Reject both exact flag tokens and `--flag=value` forms before `_reserve()`
   creates a journal and before `client.queue()` performs an external side
   effect.
3. Add the two missing attempt-02 flags:
   `--disable-async-offload` and `--disable-pinned-memory`.
4. Keep all existing loopback, output-root, model/workflow, resource and
   no-replay controls unchanged.
5. Add regression proof that every incident flag, including an assignment-form
   token, produces `ERR_GENERATION_COMFY_RUNTIME_UNSAFE`, creates no journal and
   queues nothing.

## Critic review

1. **Critical — corrective work could be mistaken for authorization of a third
   native attempt.** Resolution: the native gate remains parked and this unit
   contains no runtime launch or dispatch.
2. **High — only rejecting `lowvram` and `disable-dynamic-vram` leaves two
   incident flags independently admissible.** Resolution: reject all four
   attempt-02 memory flags.
3. **High — exact token matching can miss assignment-form arguments.**
   Resolution: canonicalize detection to the prohibited flag identity while
   retaining the original observed token in error Evidence.
4. **High — a guard added after reservation could leave a misleading durable
   execution state.** Resolution: retain the check before `_reserve()`.
5. **High — recovery cleanup could rewrite the uncertain attempt-02 journal.**
   Resolution: no recovery mutation is in scope; the existing `QUEUED /
   RECOVERY_REQUIRED` record remains untouched.

Unresolved design Critical/High findings after corrections: `0 / 0`.

## Final plan and implementation authorization

The bounded corrective implementation above is authorized. Acceptance requires:

- focused TASK-013 adapter tests PASS;
- full repository regression PASS;
- `compileall` and `git diff --check` PASS;
- no native/paid/production execution;
- no tracked or staged mutation under `evidence/native/**`;
- truthful closure that keeps native H3, Candidate/Audit binding, TASK-013
  overall completion and R4 overall completion unclaimed.

Critic/fix work is capped at two cycles. Passing mandatory gates with unresolved
Critical/High `0 / 0` advances this bounded unit without reopening the completed
hosted adapter closure.
