# TASK-065 Dependency Takeover Checkpoint — 2026-08-30

## Effect boundary

This checkpoint records read-only/advisory dependency evidence for PL-A.  It
does not satisfy D0, D1, or D2 canonical completion and creates no PL-B config,
native, connector activation, learning admission, Timeline, Resolve, Release,
Deploy, or Production effect.

## D0 — TASK-063 installer safety

- Existing parent: Draft PR #448 at
  `ca8aa736ad56e07a54120eea6ee4bfeefb68454b`.
- Non-overwriting stacked closure: Draft PR #451 at
  `8fd17ed23242d34102908a0ce19fe8ce68b7cc9f`.
- Closure covers exact predecessor/CAS serialization, descriptor/owner source
  identity re-read, complete ancestor-chain revalidation, new-target cleanup,
  failure rollback, and a single installer provision/read-back operation.
- Hosted Product tests: Ubuntu 3.11/3.12/3.13 and Windows 3.11/3.12/3.13 PASS.
- Dependency/security checks PASS.  The only non-PASS check is the expected
  shared `CHANGELOG.md` integration gate.
- Admission result: `NOT_CANONICAL / EFFECT0`; D0 requires merge into main and
  post-main read-back before PL-A may accept it.

## D1 — TASK-060 PP-A through PP-C

- Stale PR #430 was not overwritten.
- Fresh-main replacement: Draft PR #452 at
  `6e16c3ea040c503137030d51ef965cc11545290b`, based on canonical remote main
  `160c9569673fbf65a28b0f95eeb44c5b0111584f`.
- Focused PP-A: 11 PASS.  Direct TASK-019/TASK-029 regression: 72 PASS and 3
  Windows-only DPAPI skips.  Schema mirror and compileall PASS.
- The shared CHANGELOG check remains a separate lock-owned gate.  PP-B and PP-C
  do not yet provide a canonical promoted envelope/source receipt.
- Admission result: `PP_A_DRAFT_ONLY / PP_B_PP_C_MISSING / EFFECT0`.

## D2 — TASK-061 activation and migration

- Public/private readiness drift correction: Draft PR #454 at
  `0549feaa162e75d26264e38cd91fa234dfb96c31`.
- The corrected boundary fixes the released public contract at readiness v1.
  TASK-058 v2 remains exact-package private diagnostic state and is not a
  public schema or cross-process receipt.
- TASK-058 v0.23.0 is released; TASK-060 PP-C remains missing.  No CA-A, CA-B,
  CA-C, Human activation/deactivation receipt, or disabled rollback read-back
  exists yet.
- Admission result: `CONTRACT_CORRECTION_DRAFT_ONLY / CA_A_CA_B_CA_C_MISSING /
  EFFECT0`.

## Independent resume conditions

PL-A must re-open each lane independently:

1. D0 accepts only canonical main containing the TASK-063 closure plus green
   post-main tests/read-back.
2. D1 accepts only canonical PP-C with exactly one promoted envelope and source
   receipt; PP-A Draft evidence is insufficient.
3. D2 accepts only canonical CA-C explicit Human activation/deactivation
   history plus exact disabled rollback read-back; documentation is
   insufficient.
4. Any head drift, failed/pending check, stale instance, unknown issuer/version,
   multi-install ambiguity, missing receipt, or tamper remains disabled/effect0.
