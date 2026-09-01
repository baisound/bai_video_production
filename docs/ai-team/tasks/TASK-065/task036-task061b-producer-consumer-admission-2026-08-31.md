# TASK-036 -> TASK-061-B producer/consumer admission for TASK-065

Date: 2026-08-31

State: `TASK_LOCAL_DESIGN / SOURCE_START0 / PL_C_PASS0 / EFFECT0`

Source input: read-only task-local producer/consumer matrix
`D:\BAI\BAI Davinci Resolve DRFX\_task-local-checkpoints\2026-08-31-task036-task061b-producer-consumer-matrix.md`, audited against BVP
`origin/main=35cdf1ad475633dcf035e0616e979b5a8fde0c88`.

This document imports only its acceptance boundary into TASK-065. It does not
authorize TASK-036 or TASK-061-B implementation, change either owner's source,
or turn the external checkpoint into canonical Evidence.

## 1. Non-substitution rule

TASK-065 may admit the preactivation chain only when both are canonical and
current:

1. a TASK-036 producer completion receipt covering T36-A/B/S/M/R/P/E; and
2. a TASK-061-B consumer completion receipt covering A61-E/R/D/Z.

The TASK-036 serialized receipt is public-safe audit Evidence with
`authority_created:false`. TASK-061-B must independently resolve the operation,
pinned-read that receipt and every current dependency, and recompose one
coherent trusted Product snapshot before its private one-use activation
capability can exist. That private capability does not cross into TASK-065.
TASK-065 receives only the later canonical TASK-061-B completion receipt and
read-only verifies its binding to the exact TASK-036 completion receipt.

The following are never substitutes for the two-receipt chain:

- a TASK-036 durable receipt alone;
- `ConnectorSourceBindingReadiness`, `HumanActivationEvidence`,
  `InstalledAdapterE2EReadback`, activation transaction or other public
  dataclass/factory output;
- a public mapping, copy, deserialization, subclass, self-hash or module seal;
- caller booleans, timestamps, paths, mode, expected revision or authority
  strings;
- exit code zero, file/status presence, connector status or
  `canonical_store_written`;
- synthetic, source-only, fixture-only or status-only evidence.

Every substitute attempt produces `PRODUCER_CONSUMER_CHAIN.N.C. / EFFECT0`,
with TASK-065 Project/Bridge/Profile/config/history delta zero.

## 2. TASK-036 producer cells

| Cell | Canonical completion requirement | Current missing boundary | TASK-065 admission field |
|---|---|---|---|
| T36-A | Closed packaged argv dispatch before Desktop/WebView2/Shell; opaque plan+record identity only; mixed/duplicate/unknown/raw-path args fail body-free without UI fallback | no Montage packaged command or complete argv/call-zero matrix | packaged dispatch receipt, argv profile/version, Shell/UI call count 0 |
| T36-B | One private bind of TASK-061-A plan, TASK-063 instance/descriptor/owner, Project manifest/lock, TASK-067 facade, fixed Generic store/scope and exact original inbox delivery; `import_path` exact1, scan/`import_once`/private parser 0 | no TASK-036 Montage composition or physical instance/Project/delivery binding | instance/plan/Project/delivery snapshot digests and exact call counts |
| T36-S | Non-creating resolver with fixed precedence: receipt+correlation, correlation, pending, then fresh; receipt without correlation and all ambiguous/multiple/tampered states STOP; caller mode 0 | no packaged non-creating resolver or full precedence/race inventory matrix | selected private mode reason plus pre/post artifact inventories; authority_created=false |
| T36-M | FRESH/RECOVERY subtype/VERIFIED_READBACK invoke only the matching TASK-067 method; capability `ARMED -> IN_FLIGHT -> CONSUMED|FAILED_CLOSED`; no retry/copy/concurrent/caller mode | TASK-067 not completed and no unmodified Bridge integration across every mode/crash seam | typed ImportResult and bound operation state transition; `canonical_store_written` excluded |
| T36-R | Independent pinned public receipt, hidden correlation, canonical Generic/Project and Profile read-back after import; same operation/instance/config/build/expiry; no second publish; body-free output | no post-import same-snapshot read-back or cross-generation/leakage negatives | receipt/correlation/canonical/Profile physical+canonical identities and second-publish count 0 |
| T36-P | The single frozen chain `task036_shell.spec -> task036_windows_entry.py -> packaged_main()` includes the private Montage entry/composition and invokes the internally resolved installed `BAI Video Production.exe`; private dispatch exact1 occurs before probe/guard/shell/presenter (each call0); frozen payload/build/EXE identities and durable body-free receipt are pinned | existing tests prove only entry import, one-dir `COLLECT`, `console=False`, spec reuse and output name; TASK-063 installer proves hidden installed-EXE launch/wait but accepts only exit0+receipt existence, while its payload digest is a build-input claim and its acceptance JSON is permissive/path-bearing; no Montage frozen inclusion, strict installed-payload/content/identity check or installed runtime receipt exists | T36-P01-P14 package/runtime matrix, payload-tree and installed EXE identities, exact dispatch/call-zero counts; stdout/exit0, `FileExists`, build-input manifest, acceptance JSON and installer/discover are authority0 |
| T36-E | Real installed packaged invocation, exact installed bytes/build, immutable config/ticket, trusted start/end/expiry and invocation budget; command exact1; no watcher/provider/UI/network/Timeline/Release/Activation | no installed Montage command or real packaged E2E chain | canonical `TASK036_MONTAGE_PRODUCT_OPERATION_RECEIPT`, `executed:true`, exact command count and installed identity |

T36-A/B/S/M/R/P/E must all be present in one canonical producer completion
receipt. A subset, a passing exit code or the public receipt body alone is
ineligible.

The exact packaged-chain source facts and T36-P01-P14 boundary are in
`task036-packaged-exe-chain-admission-2026-08-31.md`.

## 3. TASK-061-B consumer cells

| Cell | Canonical completion requirement | Current missing boundary | TASK-065 admission field |
|---|---|---|---|
| A61-E | Trusted registry/plan resolves the operation and pinned-reads the exact T36 receipt plus TASK-058/060/063/067 evidence; only the fresh trusted read can mint a private nonserializable one-use capability | no real TASK-036 receipt consumer or complete public-authority forgery matrix | exact producer receipt identity and every dependency identity revalidated by trusted Product operation |
| A61-R | Immediately before apply, one strict same-open snapshot recomposes installed descriptor/owner/security, promoted source, baseline/Profile transport, E2E, challenge/config state, Product backend/build, user/session and trusted clock | current apply consumes public readiness; strict bounded JSON and coherent cross-generation/backend/clock currentness are missing | private recomposition receipt digest, physical identities, trusted backend/clock/session and current expiry |
| A61-D | Random durable Human challenge and trusted response; atomic consume with private capability; secure initial/existing lock; noreplace initial config, bytes+inode+revision CAS update, owned temp/fsync/prepublish/postread/directory durability; Product-authored time | caller ID/time/backend/clock and generic lock/writer remain; real ACTIVATE and secure publication matrix missing | one Human event/challenge consumption, exact config/history revision delta and pinned durable read-back |
| A61-Z | Every stale/tampered/ambiguous/replay/collision/crash fails with exact zero-or-one designed delta; entry IN_FLIGHT, success consumed, exception FAILED_CLOSED; unknown identities preserved; body-free leakage 0 | forgery/reuse/collision/initial-race/inode-swap/durability/strict-JSON/lifecycle/leakage matrix incomplete | zero-effect/duplicate/collision reason, exact all-root inventories and no-default-config/no-Timeline proof |

A61-E/R/D/Z must all be present in one canonical consumer completion receipt.
Public readiness/Human/E2E/transaction objects and their hashes remain display
or audit data even when their fields match.

## 4. TASK-065 read-only validation

PL-C preactivation validation performs no producer or consumer operation. It
pinned-reads both canonical completion receipts, verifies that A61-E/R/D/Z
bind the exact T36-A/B/S/M/R/P/E operation and its current dependencies, and
joins them with the independently observed historical stage-count 1,
`import_path` count 1, public receipt, hidden correlation, canonical state and
Profile read-back.

Acceptance requires:

- exact issuer, schema/version, operation/plan/record/source digest, installed
  instance/config/build and trusted time/expiry equality across both receipts;
- T36-A/B/S/M/R/P/E and A61-E/R/D/Z coverage all present, with no N.C./NOT_RUN/
  synthetic substitution;
- TASK-061-B's trusted recomposition and Human/config transaction currentness,
  not merely its serialized public result;
- `enabled:false` retained by final CA-C; Production Activation remains a
  separate later Human Gate;
- TASK-065 adapter/TASK-036/TASK-061 call counts all zero and local Project/
  Bridge/Profile/config/history deltas all zero; and
- body-free public result with no absolute path, private body, token, OS detail,
  secret, account or transcript.

Only then may PL-C record `PREACTIVATION_CHAIN_VALIDATED`. This is a read-only
audit validation, not connector enable authority, Production Activation,
runtime execution or a replacement receipt.

## 5. Dependency and completion Gate

The governing order remains:

```text
TASK-061-A -> TASK-067 -> TASK-036 -> TASK-061-B -> TASK-065
```

TASK-036 waits for all earlier canonical dependencies. TASK-061-B starts only
after the canonical T36-A/B/S/M/R/P/E producer completion. TASK-065 starts PL-C
admission only after canonical A61-E/R/D/Z consumer completion and all other
PL-A dependencies. Until then both receipts are missing, PL-C PASS is zero,
and source/shared/config/native/Release/install/Deploy/Production effects are
zero.
