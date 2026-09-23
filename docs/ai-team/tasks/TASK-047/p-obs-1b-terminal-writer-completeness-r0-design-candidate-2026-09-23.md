# TASK-047 P-OBS-1B terminal writer/completeness R0 design candidate

## Scope and authority

- Active Project / Task / Atomic Unit: BAI VIDEO PRODUCTION / TASK-047 / `P-OBS-1B-TERMINAL-WRITER-COMPLETENESS-R0-DESIGN`; base `main@89c38719cc2158eb26d0e3f48cd1e0a0ba645c32`; DEV-4 cross-boundary design.
- This addresses open decision 2 of the [R1 terminal gap map](p-obs-1b-native-terminal-receipt-r1-design-2026-09-23.md) within the Owner-assigned TASK-047 receipt ABI continuation. Allowed files are this candidate and one bounded TASK-047 Evidence note. The design does not change or authorize R0 schema/parser, R1 schema, Controller/OBS/native execution, TASK-082 custody, TASK-003 Asset, TASK-043 Job, TASK-046 Dataset, private media, Release or Production.
- Status: **candidate for independent DEV-4 review, not an ABI freeze or implementation authorization**. The trusted-time owner, finite numeric `B/G`, source-offset producer and exact raw readback record remain unbound. No capture START, receipt issuance or TASK-098 A5 admission follows.

## Exact-source constraints

1. The current `BaiCaptureOperation` fences new packet leases through `RequestStop`, but the UI thread can block acquiring `commitGate`; a packet lease can simultaneously block in the sink's `gate`/writer call. `BeginSettlementAsync(2000 ms)` then falls back to `AwaitSettlementWithoutDeadlineAsync`. The current Technical Preview path is not the bounded terminal producer.
2. `BaiVoiceCaptureController.FinalizeSettledOperation` disposes the float WAVE writer, moves a partial file to the final path and writes a legacy receipt. It does not prove canonical PCM24, durable same-object readback, physical identity or TASK-082 custody. No R1 terminal field may be inferred from that legacy `File.Move`.
3. R0 `CaptureTransportIntegrityReceiptV2.transport_verification_state` is `BOUND_VERIFIED | MISMATCH | UNKNOWN`, but parsing it gives only `STRUCTURAL_VALID_ONLY`. A self-consistent transport claim is not an authenticated producer fact. TASK-082 alone owns `RAW_CAPTURE` publication under `TASK047_RAW_CAPTURE_OUTPUT`; a terminal digest or opaque raw reference is not a write lease or custody receipt.

## Proposed orthogonal outcome dimensions

The R1 field matrix should represent distinct facts rather than one overloaded success flag. These names are design candidates; **do not emit or parse them yet**.

| Dimension | Candidate closed states | Meaning and exclusion |
|---|---|---|
| `capture_completeness_state` | `COMPLETE`, `INCOMPLETE`, `UNKNOWN` | `COMPLETE` requires a proven stop boundary, all owned packet leases settled, and verified source-to-accepted-frame continuity over the actual attempt interval. Human stop may end a valid shorter interval; requested duration alone is not completeness. A lost/reordered/overrun frame, ambiguous boundary or unclosed receiver cannot be `COMPLETE`. |
| `terminal_write_state` | `NO_OBJECT`, `OPEN_OR_UNSETTLED`, `CLOSED_READBACK_MATCH`, `CLOSED_READBACK_MISMATCH`, `UNKNOWN` | `NO_OBJECT` proves no raw object creation began. `OPEN_OR_UNSETTLED` is a known unfinished write, not a recoverable closed object. `CLOSED_READBACK_MATCH` requires writer close, durable same-object identity/length/hash readback. Mismatch and uncertainty are quarantined; neither is a content publication. The earlier three-state candidate is insufficient to distinguish no object from an open object and mismatch from mere incompleteness. |
| `transport_verification_state` | Existing R0 `BOUND_VERIFIED`, `MISMATCH`, `UNKNOWN` | Copied only from the exact same-attempt R0 transport record after lineage revalidation. This is a structural claim until the producer and currentness chain are independently bound. |

No field value creates Dataset, quality, Asset, encrypted custody, Consent, Job/head or Production authority. `COMPLETE` must be impossible when transport is `MISMATCH` or `UNKNOWN`, a source/OBS/device failure leaves unaccounted frames, or the independent stop supervisor has not proven the stop boundary. `CLOSED_READBACK_MATCH` is allowed with `INCOMPLETE` capture: an intact *partial* raw object is recovery material, not a complete take. `COMPLETE` with `NO_OBJECT` or `OPEN_OR_UNSETTLED` is invalid for a recording operation. Metadata-only GAIN/readiness operations are a different mode and must not synthesize a recording terminal.

## Candidate cross-state and raw-field matrix

| Capture | Writer | R0 transport | Candidate structural disposition | Raw-field rule |
|---|---|---|---|---|
| `COMPLETE` | `CLOSED_READBACK_MATCH` | `BOUND_VERIFIED` | Potentially well-formed terminal only; still `STRUCTURAL_VALID_ONLY` and not admission. | Exact opaque object ref, byte count, raw-content digest, opened physical identity digest and independently pinned readback-record digest required; no host path. |
| `INCOMPLETE` or `UNKNOWN` | `CLOSED_READBACK_MATCH` | any | Recovery terminal candidate only if all receipt deadlines and producer evidence still hold. Never a complete capture. | Same complete raw evidence as above, explicitly marked partial/uncertain in the private attempt journal. |
| `INCOMPLETE` or `UNKNOWN` | `NO_OBJECT` | any | Body-free failure terminal candidate only if noncreation is proven and deadlines hold. | All raw object/ref/content/readback fields null; no zero-byte fake object. |
| `INCOMPLETE` or `UNKNOWN` | `OPEN_OR_UNSETTLED`, `CLOSED_READBACK_MISMATCH` or `UNKNOWN` | any | No positive raw-content claim; durable `UNKNOWN`/quarantine and exact recovery readback required. A failure terminal is possible only after an independently accepted failure-evidence ABI and deadline check. | Do not expose a content digest as matched; retain known opaque attempt/object coordinates only in access-controlled recovery state until the exact public-safe nullability matrix is reviewed. |
| `COMPLETE` | anything other than `CLOSED_READBACK_MATCH` | any | Reject as internally inconsistent; never repair by changing one field during parsing. | No Asset/custody promotion. |
| `COMPLETE` | `CLOSED_READBACK_MATCH` | `MISMATCH` or `UNKNOWN` | Reject: transport does not support a complete-capture claim. | No Asset/custody promotion. |

The table does **not** claim that `BOUND_VERIFIED` authenticates transport or that a terminal can be emitted after an expired `D`. On stage timeout, blocked lock/flush, process crash or lost reply, the independent supervisor must durably record `UNKNOWN`, retain object ownership and forbid same-attempt replay. If no terminal was durably published before `D`, later recovery must not backdate or mint a fresh terminal; it may produce a separately versioned recovery record after exact evidence reconciliation. Whether such a recovery record belongs in R1 remains open.

## Readback boundary requiring producer proof

- A future write-close/readback record must be bound to `segment_attempt_id`, writer role/build, immutable operation and output-object identity, write-close observation, same-object reopened physical identity, exact byte count, content digest, readback observation and its own digest/preimage. The raw staged object ref is an opaque identifier only, never a filesystem path or capability. The issuer and private/public split are not yet allocated.
- `CLOSED_READBACK_MATCH` requires a durable journal event before the terminal is selected, then a readback of that event and the same physical object. A pre-close hash, path existence, cached byte count, file rename or self-reported terminal field does not suffice. Object replacement/reparse drift, short read, hash mismatch, flush failure and journal loss become mismatch/`UNKNOWN`, not success.
- TASK-047 can report capture facts and hand off an exact producer output role; TASK-082 independently accepts or rejects a later `RAW_CAPTURE` write under `CAPTURE_RAW_PUBLISH`. TASK-082 publication, TASK-003 Asset adoption and TASK-046 Dataset review are later separate transactions. No implicit `File.Move` or terminal-only lease is allowed.

## Required review and test plan before freeze

1. Independently review whether the five writer states are the minimal lossless partition and whether a failure terminal with known-but-unsafe object coordinates is safe. Freeze the exact field/nullability matrix and raw readback record issuer/preimage before any schema/parser implementation.
2. Pure schema/state vectors: every cross-state row and forbidden combination; `COMPLETE` with transport mismatch/unknown, open writer, missing raw evidence or zero-byte substitute; partial closed-and-matched positive recovery; duplicate stop/lost reply/restart; wrong attempt, object role, identity, digest, byte count and predecessor; strict deadline equality and expired failure terminal. The parser remains structural-only.
3. Future bounded native fault vectors under a fresh Human Gate: stuck `commitGate`, sink lock or flush; receiver cancellation resistance; crash before/after journal event and receipt publication; same-path object swap/reparse; readback mismatch; denied restart while `UNKNOWN`. An in-process timeout unit test cannot prove physical stop or durable quarantine.

Unresolved before acceptance: independent DEV-4 Critic/Tester/Judge, exact producer capability and source-frame accounting, `TrustedCaptureTimeBindingV1` owner, numeric `B/G`, readback-record ABI, public-safe failure terminal nullability and the rest of the R1 pause/acoustic matrix. No code/native test was run for this design candidate.
