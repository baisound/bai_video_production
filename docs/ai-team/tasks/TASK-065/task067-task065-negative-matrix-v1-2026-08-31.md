# TASK-067 / TASK-065 task-local negative matrix v1

Date: 2026-08-31

State: design-only; source/schema/test/native/Release/Production effects zero

This matrix is the mandatory fault-coverage projection for the future
TASK-067 Generic Review Operation Facade and TASK-065 production linkage. It
does not authorize either implementation. Public mappings, hashes, seals,
status strings and self-derived receipts are Evidence only and create no
effect authority.

The canonical dependency order is:

```text
TASK-068 -> {TASK-069, TASK-063}
TASK-063 -> TASK-060
{TASK-069, TASK-060, TASK-063, SKILL-D2S-001} -> TASK-061-A PREACTIVATION PREPARE (enabled:false)
TASK-061-A -> TASK-067
{TASK-061-A, TASK-063, SKILL-D2S-001, TASK-067} -> TASK-036 real installed E2E
TASK-036 -> TASK-061-B FINAL CA-C
all completion receipts -> TASK-065 PL-A/B/C/D
```

Any whole-task TASK-061 prerequisite for TASK-067 is **SUPERSEDED**.
TASK-061-A is the only TASK-061 input to TASK-067. TASK-061-B is later, consumes
TASK-036 real-installed E2E and remains distinct from Production Activation.

## Result and delta vocabulary

- `EFFECT0`: no Project, Bridge, Profile, config or history mutation.
- `FAILED_CLOSED`: the private operation object has burned and cannot be reused.
- `STOP_PRESERVE`: ambiguous or foreign state is preserved without repair,
  deletion or overwrite.
- `DUPLICATE`: typed terminal result proven from the exact durable same-snapshot
  state; never inferred from a public receipt or equal bytes alone.
- `ACCEPTED`: one exact operation committed and its required durable read-back
  passed.
- `N.C.`: required source, authority or executed Evidence is not confirmed.

## TASK-067 mandatory matrix

| ID | Source symbol | Precondition | Fault seam | Expected typed result | Project delta | Bridge delta | Profile delta | Config/history delta | Public leakage | Evidence receipt |
|---|---|---|---|---|---|---|---|---|---|---|
| G67-A01 | private Generic factory; `Task036LaunchConfiguration` audit mapping | Current TASK-061-A receipt and exact private composition are otherwise valid | Direct mapping/dataclass, copy, deserialize, duck type, subclass or module-token attempt to mint factory/capability | `AUTHORITY_INVALID / EFFECT0`; no capability; supplied object unusable | 0 | 0 | 0 | 0 | stable code only; mapping/body/path 0 | negative result binds attempted authority class and delta hashes; authority_created=false |
| G67-C01 | private facade methods `admit_generic_observation`, `recover_generic_observation`, `get_verified_generic_observation` | One genuine private capability is `ARMED` | Same-object retry, concurrent double call, commit-then-throw, or any call after exception | first entry `IN_FLIGHT`; success `COMPLETED`; every thrown path `FAILED_CLOSED`; later calls `EFFECT0` | exact 0/1 for first call; later 0 | exact permitted first-call delta; later 0 | 0 | 0 | body/path/capability 0 | state-transition receipt plus before/after inventories and invocation count |
| G67-M01 | Generic manifest and save-journal same-snapshot helpers | Generic existing lock then Product lock held | stat-open, read-post swap, same bytes/project_id different inode, hardlink, ancestor reparse, valid-lock-time manifest or journal swap | `CURRENTNESS_MISMATCH / STOP_PRESERVE / FAILED_CLOSED` | 0 | 0 | 0 | 0 | identity/path/value 0 | opened raw/canonical hashes, physical identities and post-read comparison reason code |
| G67-L01 | secure initial Generic operation lock | Bounded Project coordinate under pinned trusted ancestor | absent/safe-empty/prior one-byte lock; target race; unknown/orphan/nonempty/case-collision; read/status on missing lock | exact valid prior lock may proceed; race loser freshly classifies once; otherwise `STOP_PRESERVE`; status/read creates nothing | only authorized one-byte initial lock may be created; otherwise 0 | 0 | 0 | 0 | absolute lock/root 0 | initial/existing classification, handle identity, DACL/reparse/nlink proof; receipt 0 on failure |
| G67-S0 | PRECOMMIT_RESUME resolver and Generic facade | Exact Bridge pending is durable and canonical entry/journal is absent | after pending before journal; before recover entry; before/after initial lock; unrelated canonical revision; same record different digest | S0a-c fresh resume may `ACCEPTED`; S0d/e `CURRENTNESS_MISMATCH / EFFECT0 / FAILED_CLOSED` | exact one commit only for S0a-c; 0 for S0d/e | matching pending/correlation/receipt only for success; unrelated 0 | 0 | 0 | body/path/payload 0 | exact seam, pending identity/digest, resolver mode and before/after inventories |
| G67-S1 | canonical Generic journal phases and facade result/get boundary | Genuine capability selected FRESH/RECOVERY/VERIFIED_READBACK | after Project commit, after manifest advance, marker/ledger/object/readback boundaries, receipt before cleanup | seam-specific `ACCEPTED` or typed `DUPLICATE`; old object always `FAILED_CLOSED` | expected first terminal delta only; restart 0 | exact correlation/receipt add and matching pending cleanup only; unrelated 0 | 0 | 0 | body/path 0 | seam name, terminal typed result, exact Project/Bridge inventory and revision deltas |
| G67-A2 | `get_verified_generic_observation` and terminal resolver | Generic journal absent | exact committed terminal entry versus orphan, multiple, unknown, stale or mismatched entry | exact same-snapshot terminal proof only -> `DUPLICATE`; all others `STOP_PRESERVE / EFFECT0` | 0 | exact duplicate flow only when proven; otherwise 0 | 0 | 0 | record body/path 0 | manifest/binding/ledger/head/marker/object identities bound in one read receipt |
| G67-R01 | private TASK-036/TASK-067 resolver | TASK-061-A receipt and exact record/digest are current | caller mode, wrong precedence, method-mode mismatch, journal/pending/terminal race | fixed precedence selects one method; mismatch `MODE_MISMATCH / FAILED_CLOSED / EFFECT0`; no auto-refresh | 0 on mismatch | 0 on mismatch | 0 | 0 | resolver internals/path 0 | resolved mode, controlling durable identity and burned capability receipt |
| G67-B01 | late-bound Bridge actual mapping at facade entry | Exact TASK-036 operation owns one pending record | mapping created during prevalidation, raw JSON factory, repeated mapping, identity swap before entry | exactly one entry-time mapping or `AUTHORITY_INVALID / FAILED_CLOSED / EFFECT0` | 0 on failure | 0 on failure | 0 | 0 | raw JSON/private fields 0 | mapping invocation count=1 and exact operation/record/digest binding |
| G67-D01 | direct facade and Bridge integration adapters | Direct Project-only test or real Bridge integration is explicitly selected | Project-only path touches Bridge; Bridge path changes unrelated inventory; wrong pending cleanup | direct facade `ACCEPTED/DUPLICATE` with Bridge delta 0; integration permits exact correlation/receipt add plus matching pending cleanup only | exact expected Project delta | direct 0; integration exact bounded delta | 0 | 0 | private payload/path 0 | complete before/after Project and Bridge inventories plus typed result |
| G67-X01 | `BridgeApplication.import_path` call sequence and TASK-058 exact/generic APIs | Existing released Bridge sequence and Exact lane baseline are pinned | reordered/skipped/repeated call; widened Exact API; changed serialization or public receipt semantics | regression failure; TASK-067 not commit-ready; `EFFECT0` in fault fixture | 0 | 0 | 0 | 0 | no new output/body/path | unmodified call-sequence trace and TASK-058 Exact/Generic regression C/H=0 |

## TASK-065 mandatory matrix

| ID | Source symbol | Precondition | Fault seam | Expected typed result | Project delta | Bridge delta | Profile delta | Config/history delta | Public leakage | Evidence receipt |
|---|---|---|---|---|---|---|---|---|---|---|
| PL65-A01 | PL-A dependency admission and durable baseline reader | Candidate receipts are presented for TASK-069/060/061/063/067, TASK-036 and SKILL-D2S-001 | public readiness/status/code presence, old hash, caller boolean, synthetic fixture, wrong installed build or stale/cross-instance receipt | `BASELINE_N.C. / EFFECT0` until TASK-069 durable baseline plus installed exact sync and every dependency receipt passes pinned currentness | 0 | 0 | 0 | 0 | private paths/body 0 | one bound PL-A admission receipt names exact canonical/installed hashes and durable dependency receipt identities |
| PL65-B00 | TASK-068 secure file/update substrate completion receipt; PL-B source/start Gate | Canonical TASK-068 scope and receipt are offered to PL-A | temp handle loss, non-atomic expected-state CAS, path-only unlink race, Windows ancestor share-delete gap, non-durable lock, or mutable/unpinned snapshot remains open | `TASK068_P0_OPEN / PL_B_SOURCE_START0 / EFFECT0`; no PL-B implementation PASS | 0 | 0 | 0 | 0 | path/handle/OS detail 0 | TASK-068 receipt must bind retained temp handle/identity, atomic CAS, identity-safe unlink, pinned Windows ancestor sharing, durable lock and immutable same-snapshot proof |
| PL65-B01 | `BvpMontageLearningRuntimeConfigProjectionTransaction`; operation root/lock/journal/config/receipt/pointer | PL-A PASS, exact selected instance and PL65-B00/TASK-068 P0 closure are current | initial/existing lock race, safe-empty/unknown, case collision, target/inode swap, foreign temp, directory fsync failure, concurrent A/B | exact duplicate may `DUPLICATE`; ambiguity `STOP_PRESERVE / EFFECT0`; success `ACCEPTED` only after pinned durable read-back | 0 | only exact operation-owned artifact delta; unrelated 0 | 0 | one coherent immutable operation chain or 0; history 0 | absolute root/config/receipt 0 | lock/dir/journal/artifact/pointer physical identities, canonical hashes and durability proof |
| PL65-B02 | D2S trusted broker/operation ticket and immutable invocation config | One unexpired ticket binds exact command, instance, config, input and budget=1 | crash before/after launch, expiry, replay/second/concurrent call, config/receipt swap, wrong command | command effect exact 0/1; first valid call burns ticket; retry/replay `FAILED_CLOSED / EFFECT0` | 0 | exact command delta at most once | 0 | activation history 0; distribution config 0 | ticket/config/path 0 | atomic redeem/consume receipt, launch/result digest and crash recovery state |
| PL65-C01a | TASK-065 preactivation-chain admission reader; TASK-036 durable E2E receipt | TASK-036 exact-one operation is already complete and its receipt was consumed by TASK-061-B | TASK-065 tries adapter/TASK-036 invocation, second publish/import, or accepts a chain without observed stage count=1, import count=1, pinned public receipt, hidden correlation and Profile read-back | pinned read/join only -> `PREACTIVATION_CHAIN_ADMITTED`; invocation attempt or mismatch -> `EFFECT0`; adapter/TASK-036 call count from TASK-065=0 | 0 | 0 | 0 | 0 | learning/private/absolute paths 0 | admission receipt binds existing TASK-036 receipt and independently observed historical operation deltas: stage=1, import=1, exact public receipt/correlation/Profile; those observed deltas are not TASK-065 local deltas |
| PL65-C01b | TASK-065 steady-state/post-activation Product operation | Separate current Production Activation Human receipt, new operation ID and new one-shot ticket are all present | current authority has no Activation receipt; preactivation delivery/receipt/ticket reused; second publish; operation/phase ID collision | current state `START0 / GATE_REQUIRED / EFFECT0`; future execution requires a separately authorized exact 0/1 operation and never reuses preactivation state | 0 | 0 | 0 | 0 | Human/ticket/path/body 0 | separate post-activation receipt must bind Human Gate, new operation/ticket/config/input and exact execution/read-back; preactivation receipt is comparison-only |
| PL65-C02 | PL-C phase-aware verifier; adapter `canonical_store_written` audit field | Candidate preactivation or post-activation Evidence is presented | receipt-only, `canonical_store_written`, status-only, missing/wrong Profile or correlation, wrong operation/instance/config, preactivation receipt substituted for post-activation, or post-activation receipt substituted for preactivation | `E2E.N.C. / EFFECT0`; no PASS promotion and no cross-phase substitution | 0 | 0 | 0 | 0 | receipt/body/path 0 | negative verifier receipt identifies body-free phase/issuer/operation mismatch codes; authority_created=false |
| PL65-D01 | PL-D lifecycle resolver and instance-bound projection state | One exact installed instance and committed PL-C chain are current | deactivate, rollback, uninstall, upgrade, portable move, multiple/zero install, stale descriptor, attempted dual write or fixed legacy path write | exact current instance transition may `ACCEPTED`; ambiguity `STOP_PRESERVE / EFFECT0`; legacy fixed path is migration read-only | 0 | exact selected-instance transition only; user data preserved; unrelated 0 | preserved unless separately authorized | exact selected config/history transition only; dual write 0 | instance/root/user data paths 0 | lifecycle receipt binds predecessor/successor instance, preserved data inventory and no-dual-write proof |
| PL65-Z01 | release/install/Production-Activation boundary | Any subset of D0/D1/D2/D2S or PL phases reports PASS | partial PASS promoted to whole PASS; Product Activation, Release or install attempted without its separate Human Gate | `GATE_REQUIRED / EFFECT0`; TASK-065 remains N.C. | 0 | 0 | 0 | 0 | secret/private/native detail 0 | gate decision receipt identifies missing independent Gate; no authority created |

## Acceptance use

Each future focused test must record all eleven matrix columns. A test that
asserts only an exception or status string does not satisfy this matrix. Before
and after inventories must make unrelated Project/Bridge/Profile/config/history
deltas explicit, and public output capture must prove absence of private body,
path, token and capability data. Unexecuted rows remain N.C.; a PASS in one row
cannot promote another row or the whole dependency graph.
