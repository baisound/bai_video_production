# Outcome L completion consumer contract for TASK-065

Date: 2026-09-01

State: `TASK_LOCAL_DESIGN_CLOSURE / RECEIPTS_N.C. / SOURCE_START0 / EFFECT0`

## Purpose and effect ceiling

This is the one closed consumer contract for Outcome L. It assembles, but does
not replace, the detailed owner packets:

- `dependency-currentness-reconciliation-2026-08-31.md` is the currentness ledger.
- `pl-b-option-b-runtime-config-design-correction-2026-08-31.md` is the Option-B transaction boundary.
- `task036-packaged-exe-chain-admission-2026-08-31.md` is the TASK-036 producer contract.
- `task036-task061b-producer-consumer-admission-2026-08-31.md` and
  `task067-task065-negative-matrix-v1-2026-08-31.md` are the receipt and eleven-column fault matrices.

TASK-065 is a receipt consumer. It must not implement or invoke Canonical
SKILL/D2S, TASK-069, TASK-060, TASK-061, TASK-067, TASK-036, installer
discovery, adapter staging, `import_path`, activation, install, Release, Deploy
or Production Activation. This packet creates no capability and has no
source/schema/test/native effect.

The only permitted preactivation outcome is a body-free audit projection:
`PREACTIVATION_CHAIN_VALIDATED` with `authority_created:false`. It grants no
connector enablement, retry, further import or later execution.

## Canonical one-way producer graph

```text
TASK-068 -> {TASK-069, TASK-063}
TASK-063 -> TASK-060
{TASK-069, TASK-060, TASK-063, SKILL-D2S-001} -> TASK-061-A PREACTIVATION PREPARE (enabled:false)
TASK-061-A -> TASK-067
{TASK-061-A, TASK-063, SKILL-D2S-001, TASK-067} -> TASK-036 real installed Product operation
TASK-036 -> TASK-061-B FINAL CA-C
all current completion receipts -> TASK-065 PL-A/PL-B/PL-C/PL-D
```

Any old whole-TASK-061 prerequisite for TASK-067 is **SUPERSEDED**. TASK-061-B
is strictly after TASK-036; Production Activation is later still and has its
own Human Gate.

## Closed TASK-065 consumer ABI

`TASK065_PREACTIVATION_CHAIN_VALIDATION_V1` is a validation interface, not a
wire-format authorization. A future trusted Product reader must resolve every
coordinate itself from durable current receipts, strict same-open snapshots and
its own private currentness context. TASK-065 may receive only a body-free,
closed projection of the following verified bindings:

| ABI group | Required bound fields | Reject when |
| --- | --- | --- |
| Version and issuer | contract/version, issuer class, receipt identity, exact parent receipt identities and canonical parsed digest | unknown semantic field, wrong issuer/version, copied/rehashed public object or non-strict JSON |
| Operation | phase=`PREACTIVATION`, operation ID/digest, action, record/source/projection digests, trusted start/end/expiry and invocation budget | operation, phase, digest, trusted-time or budget differs across the chain |
| One-shot authorization | D2S trusted-broker redemption result digest, TASK-061-A prepare receipt digest, nonce digest and immutable operation-config snapshot digest/physical identity | v1 or reusable enabled config, raw ticket/config, caller timestamp, non-consumed/expired/replayed authority or config/receipt swap |
| Selected installation | TASK-063 install instance, descriptor/owner generation and physical identities, Product EXE/payload/build and lifecycle currentness | caller path/root, fixed ProgramData/distribution-default/scan fallback, zero/multiple/currentness-drifting installation, build-only proof, `discover` refresh or cross-install reuse |
| Stage and import | adapter stage count=`1`, TASK-036 `import_path` count=`1`, exact frozen Product dispatch and prohibited-call counters | TASK-065 invokes adapter/TASK-036, count is not one, `import_once`/scan is used, second publish/import occurs or a crash is retried |
| BVP terminal readback | pinned strict public receipt digest, hidden Generic correlation digest, canonical Generic/Project readback digest and Profile readback digest | receipt-only/status-only/`canonical_store_written`, missing/wrong correlation or Profile, cross-generation readback, body/path leakage |
| Upstream closure | TASK-069 `TASK058_BASELINE_READBACK`, TASK-060 source receipt, TASK-061-B final receipt and TASK-067/TASK-036 coverage identities | public readiness, Human/E2E/transaction types, fixture, self-hash, status, exit code or code presence substitutes for a durable completion receipt |
| Public projection | stable result/reason code plus opaque receipt/operation digests and zero local-call/delta counters | absolute path, raw learning body, correlation body, token, SID/account, OS detail, capability or private receipt field is exposed |

The source-owner coverage is unchanged: TASK-036 provides all
`T36-A/B/S/M/R/P/E` and `T36-P01..P14`; TASK-061-B provides all `A61-E/R/D/Z`.
A subset is `PRODUCER_CONSUMER_CHAIN.N.C.`. The private one-use capability used
by TASK-036 or TASK-061-B never crosses this ABI. Public receipts, hashes and
types are audit projections only.

## Closed parser, privacy and resolver boundary

Every receipt or projection used for validation is read from one pinned,
nofollow same-open snapshot. The reader rejects BOM, invalid UTF-8 or control
characters, duplicate object keys at every nesting level, `NaN`, `Infinity`,
`-Infinity`, trailing non-whitespace bytes and non-built-in JSON values. It
enforces byte, depth, object-member, array-item and string ceilings before any
canonicalization, hashing, correlation comparison or log projection. The raw
opened-bytes digest, canonical parsed digest and physical identity are one
verification result; reopening a path to prove equivalence is forbidden.

The public projection is a closed privacy projection, not recursive key-name
redaction. It rejects or omits raw UNC/drive/home/repository/URI paths, email,
account/SID, secret/token-like values, private correlation, transcript-like
text, control values and normalization/homoglyph evasions. Unknown fields,
oversize values and privacy rejects are body-free `EFFECT0`; no raw value may
reach a receipt, log, error, temporary artifact or stdout.

Only the future TASK-063 trusted selected-instance reader can choose the
installation coordinate. There is no fixed ProgramData or distribution-default
active-root fallback, directory/root scan, newest/timestamp winner, mutable
pointer, default-config omission, packaged `discover` refresh or caller-supplied
path. The distribution config remains the disabled sentinel; no validation
creates or enables a configuration.

## D2S corrective design gates before Outcome L can progress

Read-only audit of the clean D2S dedicated worktree at
`6a391336ca9985d7c2d37c1c8a0846de63fd7b7a` against
`origin/main=c86ec8c11724a3170d37e0fdc5a516979fcca703` confirms that the
existing Draft PR is a data-only safety/privacy checkpoint, not an Outcome L
completion. The focused adapter suite is `53/53` passing in WSL; this is
source-level evidence only and does not make broker or installed E2E claims.

| Gate | Required corrective contract | Mandatory negative/fault coverage | Current Outcome L result |
| --- | --- | --- | --- |
| D2S-H1 Product one-shot path | A Product-only broker must validate the same pinned v2 config identity plus action, command, operation/ticket, selected instance/build, argv/input, expiry and nonce; atomically move `ARMED -> IN_FLIGHT` before any stage; burn on success, reject, exception, timeout, cancellation, channel close, child exit and restart. Direct v1/v2 CLI commands are isolated from installed Product operation. Terminal confirmation is a distinct read-only broker query. | direct/copy/deserialized CLI config, wrong or cross command, expired/replayed/second/concurrent ticket, config swap, receipt-arrives-after-preflight, and every pre/post redemption/stage crash seam. Ticket one yields command effect exactly 0/1; terminal delivery delta 0; canonical/Profile/activation claim 0. | `BROKER_REDEMPTION.N.C. / TASK036_START0 / EFFECT0` |
| D2S-H2 contained physical identity | Resolve root and every ancestor through nofollow handles, validate regular-directory/reparse/DACL/identity constraints and use handle-relative child open/publish (or an equivalently held trusted broker handle). Retain that lease through strict parse/hash or publish plus pinned readback. Path+lstat sampling is insufficient. | ancestor stat/open/read/post swap-and-restore, junction/reparse/case/cross-volume swap, same bytes/different inode, parent swap before temp create/move/after move, and config/receipt/Profile-root replacement. Foreign or ambiguous state is preserved. | `ANCESTOR_HANDLE_CURRENTNESS.N.C. / EFFECT0` |
| D2S-M1 action closure | The v2 schema/validator must require a per-action exact null/non-null matrix: a publish operation binds its record/delivery/result and cannot borrow a Profile; a load operation binds its Profile/result and cannot borrow a record. | null-cross-action, unrelated record/Profile, altered result/input, and mixed action profile cases. | `ACTION_BINDING.N.C. / EFFECT0` |
| D2S-M2 transport-only status | Enabled `connector-status` must be explicitly transport-only with `authority_created:false`, terminal/correlation/Profile verification false, and body-free closed output. | status-only substitution, READY/default-root inference, and public output leakage. | `STATUS_AUTHORITY.N.C. / EFFECT0` |
| D2S-M3 durability seam | Maintain separate assertions for file-fsync failure before publish and directory-durability failure after publish, including preservation/current-target behavior and platform-honest native semantics. `BvpAdapterTests.test_atomic_publish_fsync_failure_has_no_target_or_temp_delta` is reproducibly passing; this row is a required future boundary test, not a recorded failure. | prepublish file fsync, postpublish directory durability, unsupported native port, foreign temp and target replacement. | `DURABILITY_BOUNDARY.N.C. / EFFECT0` |

These are D2S-owner source and test gates. TASK-065 may consume only their
future canonical release/install/readback completion receipt; it must not add a
broker, use raw paths, emulate handle authority or amend the D2S source from
this task-local consumer packet.

## Validation algorithm and phase separation

### PL65-C01a: preactivation chain validation

1. Resolve exact receipt coordinates through the trusted reader; caller paths,
   modes, config/learning/output values and expected revisions are not inputs.
2. Strict-pinned-read the producer and consumer receipts and their verified
   body-free projections. Require equality for operation, instance, config,
   build, source/record, expiry and correlation bindings.
3. Require the historical TASK-036 facts: one adapter stage, one `import_path`,
   pinned public receipt, hidden correlation, canonical readback and Profile
   readback. These are producer deltas, never TASK-065 deltas.
4. Require TASK-061-B to prove fresh recomposition of that exact TASK-036
   operation before its own final CA-C result, retaining `enabled:false`.
5. Emit only `PREACTIVATION_CHAIN_VALIDATED` or a body-free `N.C.` reason.

This phase makes adapter/TASK-036/TASK-061 calls zero and leaves Project,
Bridge, Profile, config and history unchanged. It never publishes a second time
for confirmation and never treats `canonical_store_written` as authority.

### PL65-C01b: steady-state/post-activation

This is a distinct future operation. It is `START0 / GATE_REQUIRED / EFFECT0`
until a separate Production Activation Human receipt, new operation ID, new
one-shot ticket, new immutable config coordinate and its own exact readback
exist. A preactivation delivery, receipt, correlation, config or ticket is not
reusable across this phase.

## Fixture and test-design boundary

`p0l-common-installed-discovery-receipt-fixture-v1.json` remains a synthetic,
public-safe expected-coordinate fixture. It must keep all authority/currentness/
execution/effect flags false and all local counts zero. It can exercise ABI
shape, strict-JSON, privacy and non-substitution negatives, but cannot prove
installation selection, broker redemption, adapter execution, TASK-036
execution, activation or any completion receipt.

Focused future tests must use public-safe synthetic values only and preserve
the target object on every reject. They must record the eleven columns in the
main matrix: ID, source symbol, precondition, fault seam, typed result, Project
delta, Bridge delta, Profile delta, config/history delta, public leakage and
evidence receipt.

| ID | Source symbol | Precondition | Fault seam | Expected typed result | Project delta | Bridge delta | Profile delta | Config/history delta | Public leakage | Evidence receipt |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| L65-ABI-01 | C01a validation reader | dual durable chain offered | public receipt/type/hash/fixture replaces upstream verification | `PRODUCER_CONSUMER_CHAIN.N.C. / EFFECT0` | 0 | 0 | 0 | 0 | body/path/capability 0 | body-free rejection only |
| L65-ABI-02 | C01a field binder | exact operation coordinates present | stage/import count not `1`, wrong instance/config/build/expiry, receipt-only or missing correlation/Profile | `E2E.N.C. / EFFECT0` | 0 | 0 | 0 | 0 | raw learning/correlation 0 | no validated projection |
| L65-ABI-03 | phase router | valid preactivation receipt offered | adapter/TASK-036 call, second publish/import or preactivation-to-postactivation reuse | `PHASE_OR_REPLAY_REJECTED / EFFECT0` | 0 | 0 | 0 | 0 | ticket/config/path 0 | no execution receipt |
| L65-ABI-04 | public projector | all verified bindings are current | public result includes private body/path/secret/account/SID/OS detail | `PUBLIC_PROJECTION_REJECTED / EFFECT0` | 0 | 0 | 0 | 0 | raw value 0 | suppressed body-free reason |
| L65-ABI-05 | strict reader and instance resolver | candidate receipt and install set are supplied | duplicate/non-finite/BOM/trailing/deep/oversize JSON; raw UNC/URI/email/token/transcript; ProgramData/default/scan/pointer fallback | `AMBIGUOUS_OR_UNSAFE_INPUT / STOP_PRESERVE / EFFECT0` | 0 | 0 | 0 | 0 | body/path/OS/private value 0 | no validated projection |

## Completion Gate

Outcome L design is eligible for one coherent design review only when this
packet and all linked task-local packets agree on graph, ABI, D2S corrective
gates and fault matrix.
It is not a TASK-065 implementation or operational completion.

Before a coherent design PR may be marked ready, an independent Critic must
report `C=0 / H=0` for the complete task-local design and an independent Judge
must issue PASS. Until then the design review state is `N.C.` and there is no
commit/PR/readiness promotion from this document. Any missing upstream
completion receipt keeps the affected real effect at `START0 / EFFECT0` while
the read-only design remains available for review.
