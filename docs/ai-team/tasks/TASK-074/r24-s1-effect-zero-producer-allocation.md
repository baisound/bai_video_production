# TASK-074 R24-S1 Effect-Zero Producer Allocation

Status: `OWNER_ALLOCATED / DEV-4 / SOURCE_START0 / EFFECT0`

Date: `2026-10-11`

Allocation identity: `TASK074-R24-S1-EFFECT-ZERO-PRODUCER-ALLOCATION-V1`

Owner direction: `つぎへ`

Fresh base: `origin/main@afcd4e7176884e7da79947933f086ec7c58b930a`

## Atomic unit

This allocation selects exactly the next ordered unit in R24 section 6:
`R24-S1`, the TASK-074 fake/non-biometric effect-zero producer. R24-S0 and
R24-S0A are closed. R24-S2 and every later source/runtime unit remain outside
this allocation.

The producer may exercise the R24 exhaustive branch predicate with body-free
synthetic coordinates. It must remain fixture-only, one-use, owner-acceptance
bound, sealed and non-serializable. It must not mint or impersonate any
canonical R24 runtime current/fact/terminal type.

## Exact Allowed Files

- `docs/ai-team/tasks/TASK-074/task.md`
- `docs/ai-team/tasks/TASK-074/r24-s1-effect-zero-producer-allocation.md`
- `src/ai_video_production/owner_voice_authority.py`
- `tests/test_task074_owner_voice_authority.py`
- `docs/ai-team/tasks/TASK-074/r24-s1-effect-zero-producer-completion-receipt.md`

No schema file is allocated because the S1 producer and its decision object
must not have a JSON/mapping serialization surface.

## Required invariants

1. Construction binds the exact TASK-074 R24 Owner acceptance record digest
   `8EDDD5E86CD21A779ADBCF889A9478E67520F4E0E48748983D7ABE6F2D710BB0`.
2. Inputs use only closed enums, bounded synthetic identifiers and body-free
   digests. Strings, booleans, mappings, historical types and alternate enums
   cannot substitute for closed R24 values.
3. The branch function is total and ordered exactly as R24 section 4:
   `SUCCESS_CLOSED`, `NONCURRENT_CLOSED`, `ABORTED_CLOSED`, otherwise
   `CONTAINED_PARTIAL_TRUTH`.
4. The producer is single-use and burns on first evaluation entry, including
   rejected input. Concurrent callers have at most one winner.
5. The result is sealed, identity-only, non-copyable, non-pickleable,
   non-iterable and has no `to_dict`, `from_dict`, mapping or public-body
   surface.
6. Every result remains `fixture_only=true`, `source_authority=false`,
   `effect_authority=false`, `canonical_runtime_type_minted=false`, with zero
   child/process/private-body/model/provider/audio/WAV/publication effects.
7. No filesystem, network, subprocess, native API, Provider, model, audio body,
   Project store or external operation is entered.

## Acceptance

- focused R24-S1 positive, negative, replay and concurrency tests PASS;
- existing TASK-074 authority tests PASS;
- direct TASK-074 regression PASS;
- `git diff --check` PASS and exact Allowed Files only;
- independent DEV-4 Tester/Critic/Judge return PASS with unresolved
  Critical/High `0/0`;
- the completion receipt is committed and read back;
- hosted checks and merge completion remain required before R24-S1 closes.

Until all acceptance conditions pass, status remains `SOURCE_START0 / EFFECT0`.
This allocation grants no R24-S2, TASK-014, coordinated-amendment,
private/native/model/provider/audio/WAV, publication-current, TASK-041 PASS,
TASK-036 Gate PASS, Final Review, Release, Deploy or Production authority.
