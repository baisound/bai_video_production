# TASK-065 P0-L common installed discovery/receipt harness

Date: 2026-09-01
Contract: `TASK065-P0L-COMMON-INSTALLED-DISCOVERY-RECEIPT-V1`
Profile: `DEV-4 / DESIGN_PACKET / EFFECT0`

## Decision

P0-L Montage learning linkage, P0-E packaged QA and the future P0-V WAV QA
lane share one installed-product currentness input. They do not share effect
authority. The common harness separates three objects that must never be
collapsed:

1. a public-safe expected-coordinate plan;
2. a future Product-private, one-use installed currentness lease produced by
   the trusted TASK-063/TASK-072 composition; and
3. a body-free public receipt projection used only for audit and UI readback.

The versioned fixture in
`p0l-common-installed-discovery-receipt-fixture-v1.json` represents only item
1. It fixes `fixture_only:true`, `authority_created:false`,
`currentness_selected:false`, `installed_snapshot_verified:false` and every
effect flag to false. Its TASK-072 digest is the accepted design receipt, not
an implementation completion receipt.

## Responsibility boundary

TASK-065 is an integration consumer. It does not scan installation roots,
select a registration, invoke packaged `discover`, publish installer readback,
start the adapter, call TASK-036, read a WAV body, enable the connector, install
software or activate Production.

The future trusted producer must resolve the complete current-registration set
through TASK-063, classify cardinality as zero/one/multiple, and bind exactly
one selected installation only when the Product-owned selector proves it is
current. The same private snapshot binds:

- selected installation and immutable descriptor/owner generations;
- installed Product package, EXE and payload-tree bytes;
- opened physical identities, ancestor/DACL/reparse/nlink evidence;
- build and lifecycle predecessor/successor currentness;
- TASK-072 broker/runtime implementation identity; and
- Product clock, boot/session coordinate and expiry policy.

A path, timestamp, directory scan, public self-hash, copied fixture, exit code,
status string or code-presence check cannot select currentness or mint a
capability.

## Private currentness lease and lane authority

Each lane receives its own private currentness lease derived from the same
trusted snapshot. That lease is `authority_created:false / effect0`; it cannot
start the packaged EXE, adapter, TASK-036, WAV access or any other lane effect.
An effectful future lane must also consume a separate owner-issued one-shot
authority: the P0-E native QA Gate, the P0-V media/WAV QA Gate, or the exact
P0-L Product-operation Gate. Missing either input is effect zero. The lease
lifecycle is:

```text
ARMED -> IN_FLIGHT -> COMPLETED
                    -> FAILED_CLOSED
```

Entry consumes the lease validation budget. Success and every exception burn
the lease. Retry requires a fresh authoritative resolution. Copy,
serialization, replay, concurrent use and cross-lane substitution have effect
zero. The independent lane authority has its own one-shot lifecycle and cannot
be substituted for the lease. The public receipt projection is accepted in
place of neither private input.

## Lane bindings

### P0-L Montage learning

Preactivation admission is read/join only. TASK-065 observes an already
completed historical Product operation with adapter stage count exactly one,
TASK-036 import count exactly one, pinned public receipt, hidden Generic
correlation, canonical readback and advisory Profile readback. TASK-065 itself
calls the adapter and TASK-036 zero times and changes Project, Bridge, Profile,
config and history zero times. A second publish is prohibited and
`canonical_store_written` has authority zero.

Steady-state/post-activation execution is a different operation ID and ticket
and remains START0 without a separate Production Activation Human receipt.
Preactivation delivery, receipt or ticket reuse is rejected.

### P0-E packaged QA

The common receipt supplies installed package/EXE/payload/build and selected
instance currentness only. P0-E retains its own packaged-start, first-run,
single-instance, startup-settings, UI/readback and recovery assertions. The
common receipt cannot claim that an EXE was started or that packaged QA passed.

### P0-V WAV QA

P0-V is a future consumer lane. It may reuse installed runtime currentness but
must supply a separate WAV artifact/QA receipt. The common receipt cannot
authorize WAV body access, decoding, playback, inference, Provider use, media
mutation or a quality claim. No Owner audio or transcript content appears in
the fixture, diagnostics or public receipt.

## Producer and consumer order

The one-way dependency order remains exactly:

```text
TASK-068 -> {TASK-069, TASK-063}
TASK-063 -> TASK-060
{TASK-069, TASK-060, TASK-063, SKILL-D2S-001} -> TASK-061-A PREACTIVATION PREPARE (enabled:false)
TASK-061-A -> TASK-067
{TASK-061-A, TASK-063, SKILL-D2S-001, TASK-067} -> TASK-036 real installed E2E
TASK-036 -> TASK-061-B FINAL CA-C
all completion receipts -> TASK-065 PL-A/PL-B/PL-C/PL-D
```

SKILL-D2S-001 joins TASK-061-A and TASK-036 only at the edges above. The
TASK-072 implementation receipt joins PL65-H01 before any common private
currentness lease may be issued; its design digest in the fixture is Evidence
only. TASK-070/TASK-071 have no authority-bearing TASK-065 fixture field and
remain N.C. until their producer-defined completion receipts and exact consumer
coordinates are canonically assigned. Real consume stays parked until
TASK-063, TASK-072 and the lane-specific producer/owner receipts are current.

## Fault and recovery acceptance

The table below is a compact design index. The authoritative eleven-column
delta/leakage/receipt rows are `PL65-H01` through `PL65-H03` in
`task067-task065-negative-matrix-v1-2026-08-31.md`.

| ID | Fault seam | Expected result | Local delta / public output |
|---|---|---|---|
| IDR-01 | zero or multiple current registrations | `NOT_CONFIRMED / STOP_PRESERVE` | all deltas 0; roots omitted |
| IDR-02 | mixed instance/build/payload/descriptor/owner generation | `CURRENTNESS_MISMATCH / FAILED_CLOSED` | all deltas 0 |
| IDR-03 | same bytes, different inode; ancestor/DACL/reparse/nlink drift | `PHYSICAL_IDENTITY_MISMATCH / FAILED_CLOSED` | all deltas 0; identity body omitted |
| IDR-04 | upgrade/uninstall between plan and consume | `LIFECYCLE_STALE / FAILED_CLOSED` | fresh resolution required |
| IDR-05 | copied/rehashed fixture or missing TASK-063/TASK-072 implementation receipt | `AUTHORITY_INVALID / EFFECT0` | capability 0 |
| IDR-06 | replay, concurrent consume or exception retry | first entry only; later `FAILED_CLOSED` | effect exact 0/1 in owning lane only |
| IDR-07 | P0-L stage/import count 0 or 2, second publish, receipt-only, missing correlation/Profile | `PREACTIVATION_CHAIN.N.C. / EFFECT0` | TASK-065 calls/deltas 0 |
| IDR-08 | P0-E EXE/build/first-run/startup-settings mismatch | `PACKAGED_QA.N.C. / EFFECT0` | no launch claim |
| IDR-09 | P0-V wrong/reused WAV receipt or WAV body/Provider claim | `WAV_QA.N.C. / EFFECT0` | audio/body/provider access 0 |
| IDR-10 | P0-L/P0-E/P0-V receipt substitution | `LANE_MISMATCH / FAILED_CLOSED` | all deltas 0 |
| IDR-11 | path, SID/account, token, hidden correlation, OS detail or media body in public output | `PUBLIC_PROJECTION_REJECTED` | raw value echo 0 |

Recovery never scans for a winner, repairs an ambiguous document, deletes a
foreign object or reuses a burned capability. It begins with a fresh trusted
registration and installed snapshot read.

## Versioned fixture acceptance

The fixture is eligible only as a static, public-safe design input when:

- its exact closed top-level shape and contract/version match;
- strict UTF-8 parsing rejects duplicate keys and non-finite numbers;
- every authority/currentness/execution/effect claim is false;
- each lane is `NOT_CONFIRMED` and exposes only its expected future checks;
- P0-L historical counts are labelled expectations, not observed local deltas;
- all TASK-065 local call/delta counts are zero; and
- the serialized document contains no absolute path, account/SID, private
  correlation, WAV body, transcript, token or OS error detail.

Static fixture PASS does not satisfy PL-A/B/C/D, packaged QA, WAV QA,
Production Activation, install, Release or Deploy.

## Bounded Unit completion checkpoint

- Worktree: `task065-option-b-design-correction`.
- Branch: `codex/task-065-option-b-design-correction`.
- Pre-commit HEAD/upstream: `f855542c8ac29941f274c4a30a674caddbf72fa7`.
- Scope: this packet, its versioned fixture, the TASK-065 task pointer, three
  eleven-column negative-matrix rows and one focused static contract test.
- Focused Windows Python 3.12: `47 passed`.
- Targeted TASK-065/TASK-058/TASK-061/TASK-036 boundary regression:
  `161 passed, 2 skipped`; both skips are the existing
  `FIFO fixture unavailable` condition and are not promoted to PASS.
- JSON parse, nested closed shape/type/grammar, strict duplicate/non-finite,
  byte/depth/item/string/control, privacy and Boolean-as-integer substitution
  negatives: PASS.
- `git diff --check`: PASS with line-ending conversion warnings only.
- Independent final review: `C=0 / H=0 / M=0 / L=0`; Critic PASS, Tester PASS,
  Judge PASS.
- Real installed/native/adapter/WAV/install/Release/Deploy/Production effects:
  zero. TASK-063/TASK-072 implementation and lane-owner receipts remain N.C.
