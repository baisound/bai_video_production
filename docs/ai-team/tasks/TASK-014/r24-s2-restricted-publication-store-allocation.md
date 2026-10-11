# TASK-014 R24-S2 Restricted Publication Store Allocation

Status: `OWNER_ALLOCATED / DEV-4 / SOURCE_START0 / EFFECT0`

Date: `2026-10-11`

Allocation identity: `TASK014-R24-S2-RESTRICTED-PUBLICATION-STORE-ALLOCATION-V1`

Owner direction: `次の R24-S2 を新規に割り当て・開始してよい`

Fresh base: `origin/main@598587b574eb7859997876b167f150c2ff2dfb3d`

## Atomic unit

This allocation selects exactly the next ordered unit in R24 section 6:
`R24-S2`, the TASK-014 restricted store/current-read effect-zero source. R24-S0,
R24-S0A and R24-S1 are closed. R24-S3 and every later amendment, live source or
runtime unit remain outside this allocation.

S2 may implement only:

- a sealed restricted consumer that accepts the exact current R24-S1 effect-zero
  type and the accepted TASK-014/TASK-074 envelope pair;
- a body-free `TASK014_LOCAL_PRIMARY_NARRATION_POST_RECEIPT_V1` synthetic
  candidate parser and schema;
- append-only, Project-scoped, tamper-evident history through an in-memory fake
  persistence port; and
- an owner-authenticated sealed current-read interface that can report only an
  effect-zero contract current or a distinct fail-closed state.

It must not use a filesystem/project store, network, process, private handle or
body, model, Provider, audio/WAV, Asset, canonical publication receipt/current
type, TASK-041 PASS or TASK-036 Gate result.

## Exact input bindings

- TASK-014 R24 Owner acceptance record SHA-256:
  `A398A9FE13F886DC6A4783B2AB3EEAB61721598F20F27ABAC2C0EB2811CBB06B`
- TASK-074 R24 Owner acceptance record SHA-256:
  `8EDDD5E86CD21A779ADBCF889A9478E67520F4E0E48748983D7ABE6F2D710BB0`
- R24-S1 completion receipt checkout-byte SHA-256:
  `899F74513B141255B5B052431AADE820EE3DD118E174122B05E5AC663827152D`
- R24-S1 source checkout-byte SHA-256:
  `B2450071427D2752C4FF381746EE680E1025C8E8BB89AD6FAB1C81EDA4CC2BD3`

Equal hashes, public mappings, copied objects, alternate enums, historical
types or an unissued S1-shaped object cannot replace the exact S1 result and
sealed TASK-014 consumer identities.

## Exact Allowed Files

- `docs/ai-team/tasks/TASK-014/task.md`
- `docs/ai-team/tasks/TASK-014/r24-s2-restricted-publication-store-allocation.md`
- `src/ai_video_production/task014_r24_publication_store.py`
- `tests/test_task014_r24_publication_store.py`
- `schemas/task014-r24-publication-history.schema.json`
- `src/ai_video_production/schema_resources/task014-r24-publication-history.schema.json`
- `docs/ai-team/tasks/TASK-014/r24-s2-restricted-publication-store-completion-receipt.md`

No existing TASK-074 source, owner acceptance envelope, R24 contract, cross-
owner amendment, canonical runtime type or unrelated schema may change.

## Required invariants

1. The consumer is exact-type, sealed, non-copyable, non-pickleable,
   non-iterable, non-mapping, one-use and burns on first entry, including
   rejected input. Concurrent callers have at most one winner.
2. The accepted S1 input is an owner-issued/provenance-valid S1 decision whose
   exact synthetic Project, operation and ticket coordinate recomputes to its
   sealed digest. S2 accepts only the all-UNKNOWN contained effect-zero tuple;
   no S1 known-closed branch can be relabelled as a POST candidate.
3. Every POST candidate binds exact Project, operation, ticket, candidate,
   call, sink, result, publication-readback, S1 coordinate and S1 decision
   coordinates. It is body-free, fixture-only, publication-current false and
   carries no source/effect authority.
4. History is append-only, Project-scoped, revision/parent chained, bounded,
   canonical and tamper-evident. A replacement requires exact snapshot CAS.
5. Current read selects only one intact latest operation/candidate head and
   distinguishes store missing, record missing, stale upstream coordinate,
   broken chain, foreign Project and unsafe authority flags.
6. The current-read result is sealed, owner-origin authenticated and
   nonserializable. Even its positive S2 state is only
   `CURRENT_EFFECT_ZERO`; `PUBLISHED_READBACK_VERIFIED` and
   `Task014NarrationPublicationCurrentReadV1` are not mintable in S2.
7. The fake port stores bytes in memory only. No filesystem, Project store,
   network, subprocess, native API, Provider, model, audio body, WAV, Asset,
   publication or external operation is entered.

## Acceptance

- focused R24-S2 parser/schema, chain, current-read, negative, replay and
  concurrency tests PASS;
- direct TASK-014 regression and existing TASK-074 authority tests PASS;
- `git diff --check` PASS and exact Allowed Files only;
- independent DEV-4 Tester/Critic/Judge return PASS with unresolved
  Critical/High `0/0`;
- the completion receipt is committed and read back;
- hosted checks and exact merge completion remain required before R24-S2
  closes.

Until every condition passes, status remains `SOURCE_START0 / EFFECT0`. This
allocation grants no R24-S3, coordinated amendment, real persistence, private/
native/model/provider/audio/WAV, `NarrationPublicationReceipt`, publication-
current, TASK-041 PASS, TASK-036 Gate PASS, Final Review, Release, Deploy or
Production authority.
