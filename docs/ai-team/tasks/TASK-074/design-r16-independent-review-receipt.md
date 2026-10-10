# TASK-074 R16 Independent Review Receipt

Status: `FAIL_REVISE / SOURCE_START0 / EFFECT0`

Date: `2026-10-10`

Reviewed PR: `#603`

Reviewed head: `0af1772358688fd3a307bae3dd6ffb7e89f8ebf8`

Reviewed R16 SHA-256:
`42490B33BB7061A6BCE65F537CB82DFBF51CEB3B3F9E24B1249D5E8B0789D732`

## Independent decisions

- DEV-4 Tester: `FAIL`, findings `Critical/High/Medium/Low = 0/1/1/0`;
- DEV-4 Critic: `REVISE`, findings `Critical/High/Medium/Low = 0/4/2/0`;
- Judge: not run because Tester and Critic found unresolved High findings.

The review made no repository, audio, model, native, provider, publication or
external state change.

## Accepted diagnosis

The TASK-014 D4 and unmerged TASK-074 R15 source-start rules form a real cycle.
R16's `contract -> effect-zero -> live` separation is directionally correct,
and its proposed S1-S6 graph has no graph-theoretic cycle. R16 nevertheless
does not provide a reachable and safely closed first step.

## Required corrections

1. Add an explicit pre-S1 cross-owner acceptance stage. TASK-014 and TASK-074
   must each issue a distinct owner contract-acceptance identity. Independent
   review cannot mint either owner's authority.
2. Replace generic live prerequisites with a closed owner/type table covering
   TASK-043, TASK-046, TASK-066, TASK-068 when used, TASK-071, TASK-072,
   TASK-074, TASK-075 and TASK-076. Every missing row must result in
   `DEPENDENCY_NOT_CONFIRMED / EFFECT0`.
3. Close the current TASK-036 generic AUDIO_COMPLETION constructor path. A
   future adapter must accept only a non-substitutable TASK-041 owner-issued
   verified-current PASS type, and the generic external-gate path must reject
   AUDIO_COMPLETION.
4. Move R15's direct-transfer, partial-transfer, parent-close, per-role truth,
   terminal-union, reply-loss and no-replay rules into the current normative
   amendment instead of referring to unmerged historical Evidence.
5. Define owner-specific nominal types, mint/read APIs, seals, currentness and
   serialization/public-construction prohibitions for all three completion
   levels.
6. Synchronize the TASK-014 and TASK-074 canonical Task records with the new
   candidate, Allowed Files and precedence without granting source authority.

R16 remains `SOURCE_START0`. A corrected exact-byte successor requires fresh
independent Tester, Critic and Judge review before any source allocation.
