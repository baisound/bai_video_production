# TASK-036 packaged EXE chain admission for TASK-065

Date: 2026-08-31

State: `TASK_LOCAL_SOURCE_BACKED_REFINEMENT / TASK036_START0 / PL_C_PASS0 / EFFECT0`

Source baseline: BVP `origin/main`
`35cdf1ad475633dcf035e0616e979b5a8fde0c88`.

This document records a read-only packaging/currentness boundary. It does not
authorize TASK-036 source or test changes, build or install an EXE, invoke an
installer/discovery command, or create runtime Evidence.

## Observed distribution chain

The current distribution chain is:

```text
packaging/task036_shell.spec
 -> packaging/task036_windows_entry.py
 -> ai_video_production.task036_packaged_entry.packaged_main()
 -> normal desktop shell path
```

The spec is one-dir (`COLLECT`) and `console=False`. The root
`build-windows-exe.bat` builds that spec and expects
`builds/BAI Video Production/BAI Video Production.exe`. Existing packaging
tests statically assert the entry import, one-dir collection, `console=False`,
spec reuse and output name. This is useful historical build-contract Evidence,
but it does not prove that a future Montage private route and all of its
composition modules are present in the frozen payload, nor that the built or
installed EXE executed that route.

Current `packaged_main()` has a closed pre-shell installer route and otherwise
runs native probe, single-instance guard and desktop shell. It has no Montage
Product-operation route. Adding the future private Montage dispatch at this
single packaged boundary is the correct ownership shape, but no such route or
completion receipt exists on the baseline.

### Installed-EXE invocation precedent is not receipt precedent

`packaging/task063_main_installer.iss` already invokes the installed
`{app}\BAI Video Production.exe --bvp-installer-bridge provision-readback ...`
with `SW_HIDE` and `ewWaitUntilTerminated`. This proves an installed private
command can be launched and awaited from the packaged Product flow. It does not
prove trusted completion: the installer accepts process exit zero, then checks
only that `installer-readback.json` exists and that its prepared ancestor
snapshot still matches before logging PASS. It does not pinned-read or strictly
parse the receipt body and does not bind receipt, descriptor, owner, Product
payload or opened physical identity in one current snapshot.

That historical pattern is therefore `EXISTENCE_ONLY_PRECEDENT`, not D0,
PL-A, TASK-036 runtime or PL-C Evidence. TASK-063 requires its separately owned
corrective same-open strict receipt-content/identity read-back. TASK-036 may
reuse only the hidden installed-EXE launch/wait shape; it must not copy the
exit0-plus-`FileExists` success predicate.

## Producer completion boundary

TASK-036 completion must bind all of the following in one durable body-free
`TASK036_MONTAGE_PRODUCT_OPERATION_RECEIPT`:

- the exact canonical source/build inputs and frozen Product payload-tree
  identity, including the Montage entry and every directly required private
  composition module;
- the exact installed Product registration, EXE bytes/physical identity and
  selected TASK-063 installation generation, resolved internally rather than
  accepted as a caller path;
- one real invocation of that installed `BAI Video Production.exe`, not a
  source-Python call, import-presence check, PyInstaller analysis artifact or
  build-directory smoke;
- closed private argv dispatch exact1 before native probe, single-instance
  guard, shell and error presenter, with probe/guard/shell/presenter call counts
  all zero for the Montage route;
- opaque operation/record input resolved through the trusted Product operation,
  immutable config and one-shot ticket; raw config/learning/output/EXE/root
  paths remain ineligible caller input;
- adapter stage exact1 and TASK-036 `import_path` exact1, followed by pinned
  strict public receipt, hidden correlation, canonical Generic/Project and
  Profile read-back current to the same operation, instance, config, Product
  build and payload tree;
- trusted start/end/expiry, atomic consume and exact zero-or-one designed
  effect across every launch/crash seam; and
- installer/discover call count zero. `T63-PACKAGED-DISCOVER-EFFECT0` is a
  current High FAIL because packaged `discover` publishes fixed installer
  readback. It cannot refresh or manufacture the registration read used by the
  operation. Any necessary preflight consumes only the future
  `T63-INTERNAL-DISCOVERY-READONLY` completion with
  `DISCOVERY_READONLY=true / INSTALLER_READBACK_PUBLISH=false`, exact pinned
  descriptor+owner identity and prior durable installer receipt agreement.

Because the EXE is `console=False`, stdout presence/absence and process exit
zero are not runtime authority or receipt substitutes. Runtime PASS comes only
from the durable operation receipt plus independently pinned receipt,
correlation, canonical and Profile currentness. Public output contains only a
stable status/reason and opaque hashes/counts; it exposes no path, payload,
correlation body, OS detail, account, SID or private learning content and has
`authority_created:false`.

## Focused producer/admission matrix

| ID | Precondition | Fault seam | Required result/evidence |
| --- | --- | --- | --- |
| `T36-P01` | current spec and Windows entry | future Montage module exists in source but is absent from frozen analysis/payload | build/package completion fails; runtime receipt 0 |
| `T36-P02` | frozen payload contains a same-named module | module/build digest differs from canonical completion input | `PAYLOAD_CURRENTNESS_MISMATCH / EFFECT0` |
| `T36-P03` | installed registration is current | caller supplies EXE/root or build-directory EXE instead of Product resolver | `AUTHORITY_INVALID / EFFECT0`; process call 0 |
| `T36-P04` | exact installed EXE is resolved internally | EXE/registration/payload/descriptor changes before launch or before terminal capture | capability burns `FAILED_CLOSED`; receipt 0; no retry |
| `T36-P05` | private Montage argv is valid | dispatch occurs after probe, guard or shell startup | focused call-zero assertion fails; operation PASS 0 |
| `T36-P06` | Montage dispatch selected | probe, guard, shell or presenter is called | `DISPATCH_BOUNDARY_VIOLATION / EFFECT0` |
| `T36-P07` | frozen EXE returns exit zero | durable operation receipt is absent or incomplete | runtime/E2E PASS 0; stdout/exit authority 0 |
| `T36-P08` | console-free EXE emits no stdout | caller treats silence, process exit or file presence as success | `RUNTIME_EVIDENCE.N.C. / EFFECT0` |
| `T36-P09` | exact operation/ticket/config is current | installer or packaged `discover` is called to refresh selection | prohibited-call failure; registration/config delta 0 |
| `T36-P10` | stage/import completed exact1 | public receipt lacks hidden correlation, canonical or Profile currentness | terminal E2E receipt 0; no second publish/import |
| `T36-P11` | crash occurs before/after dispatch, stage, import or read-back | same ticket/EXE operation is replayed | first effect exact0/1; replay `FAILED_CLOSED / EFFECT0` |
| `T36-P12` | public receipt/result is emitted | path, body, correlation, OS/account/SID or private value appears | body-free receipt 0; raw bytes absent from logs/temp/public output |
| `T36-P13` | installed private command returns exit0 and creates a receipt path | caller copies TASK-063 installer precedent and checks `FileExists`/ancestor only, without strict same-open content+identity and receipt/correlation/canonical/Profile verification | `EXISTENCE_ONLY_EVIDENCE / PACKAGED_RUNTIME.N.C. / EFFECT0`; the file is preserved and PASS/receipt authority remain zero |
| `T36-P14` | descriptor carries `installer_manifest_sha256` and acceptance script reports PASS | build-input payload-tree hash or permissively parsed absolute-root acceptance JSON is substituted for installed EXE/payload bytes and current registration proof | `BUILD_INPUT_CLAIM_ONLY / INSTALLED_PAYLOAD.N.C. / EFFECT0`; internally rehash exact installed payload under trusted same-open/bounded operation |

Focused TASK-036 tests must add the Montage entry/module frozen-inclusion
contract in addition to the existing packaging assertions. Those tests remain
static package-contract Evidence. The real-installed E2E test must separately
invoke the internally resolved installed EXE and verify the durable receipt and
current receipt/correlation/Profile chain. Neither class may substitute for
the other.

## TASK-065 admission

TASK-065 PL-C never runs this producer operation. PL65-C01a pinned-reads the
already completed TASK-036 and TASK-061-B receipts and admits them only if the
TASK-036 receipt covers T36-A/B/S/M/R/P/E and T36-P01-P14. The historical
stage/import deltas belong to TASK-036; TASK-065 local Product/Project/Bridge/
Profile/config/history deltas and adapter/TASK-036/installer calls are all
zero. A later PL65-C01b operation requires a distinct Production Activation
Human receipt and a new operation/ticket; the preactivation packaged receipt
cannot be replayed or substituted.

Until the producer implementation, focused packaging coverage, real-installed
execution and canonical completion receipt all exist, TASK-036 and PL-C remain
`START0 / EFFECT0`.
