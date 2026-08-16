# TASK-036 P-UX-2A0 — Element / Selection Contract Inventory

Date: `2026-08-17`
Base: `3daf14163b3547c9999ac26ddd5324fa234d33e0`
Unit: `TASK-036 / P-UX-2A0`
Effect: `DATA_ONLY / NO_PROVIDER_OR_MEDIA_EFFECT`

## Design

P-UX-2A0 adds a pure markup-to-contract compiler. It accepts already supplied
V6.1.1 mock/runtime markup and emits one deterministic union inventory. The
compiler does not open files, execute JavaScript, launch a browser or Provider,
or treat a visual selection as Product truth.

The inventory covers the required element classes: buttons, inputs,
textareas, selects, labels, cards, lists, tabs, selected/state surfaces and
result projections. Each stable coordinate is classified as exactly one of:

- `BOUND`
- `NAVIGATION`
- `DISABLED_WITH_REASON`
- `DYNAMIC_CONDITIONAL`
- `INTENT_ONLY`
- `MISSING`

All selectable records also carry the required lifecycle contract:

```text
choice source
  -> selected coordinate
  -> current-valid / rights-license / capability / resource / freshness validation
  -> owning-service typed receipt
  -> fresh same-screen canonical read-back
  -> exact next-page identity fields
```

These are required coordinates, not claims that the later receipts already
exist. `MISSING`, `INTENT_ONLY`, stale or unknown state cannot become success
through a label, toast or local JavaScript state.

## Canonical ownership

The closed page registry has the Shell plus all 14 primary pages. It points to
the existing owners only: TASK-003/005/007/011/013/014/016/022/026/027/
036..044/046/048 as applicable. It creates no second Project, Scene, Asset,
Prompt, Candidate, Timeline, audio, QA or Export store.

The Audio page is registered as a read-only dependency boundary. This unit
does not change TASK-041, TASK-046, TASK-047, TASK-048 or Developer2-owned
implementation files.

## Deterministic receipt

The canonical source audit currently records:

| Surface | Pages | Buttons | IDs | Selects | Input/textarea |
|---|---:|---:|---:|---:|---:|
| Mock source | 14 | 231 | 203 | 41 | 75 |
| Runtime source | 14 | 126 | 106 | 2 | 6 |
| Prior live mock DOM | 14 | 253 | 205 | 57 | 83 |
| Prior live runtime DOM | 14 | 126 | 109 | 2 | 7 |

Source and live-DOM counts remain distinct. The compiler can consume a bounded
serialized live DOM later, but the prior count-only browser audit is not
invented into element rows. The current checked-in source union contains 581
contract rows and deliberately remains incomplete: 402 are `MISSING`.

Canonical JSON uses sorted keys and compact UTF-8 encoding. The inventory
digest therefore changes when either markup, the page registry, a state, a
lifecycle requirement or a record changes.

## Bounds and negative matrix

- markup: `1..2,000,000` UTF-8 bytes per surface;
- contract rows: maximum `2,000` per surface; row `2,001` rejects;
- exact 14-page registry required;
- duplicate element coordinate or stable ID rejects;
- missing runtime selector remains `MISSING` even if a toast repeats its text;
- a static disabled control without a reason is `INTENT_ONLY`, not a truthful
  blocked contract;
- navigation is route state, not Product apply Evidence;
- Provider execution, Human decision and external-effect flags are fixed
  false and fail closed if promoted.

## Verification

- focused P-UX-2A0 tests: `11 passed`;
- adjacent TASK-036 regression: `105 passed`;
- full WSL2 regression: `1692 passed / 1 intentional Windows-only skip`;
- compileall: PASS;
- deterministic digest/equality: PASS;
- page/service/handoff registry: PASS;
- missing/intent/disabled/navigation negative tests: PASS;
- cap and cap+1: PASS;
- filesystem/process/network/Provider surface scan: PASS;
- adjacent TASK-036 regressions and full repository regression: required
  before merge.

## Critic

### Builder / Completeness

Finding: counting buttons alone would repeat the original audit defect.
Resolution: the compiler includes fields, labels, cards, lists, tabs, state
and result projections, and keeps source/live-DOM counts separate.

### Security / Authority

Finding: a selected CSS class or runtime label could be mistaken for approval
or execution authority. Resolution: lifecycle fields are explicitly required
future Evidence; all effect/Provider/Human-authority booleans are false and
guarded.

### Operations / Compatibility

Finding: reimplementing page owners would conflict with completed TASK-027 and
TASK-037..045 or Developer2 audio work. Resolution: the closed registry only
references their contracts. The compiler is data-only and has no filesystem,
process, network or media surface.

Residual Critic `C/H/M = 0/0/0`.

## Independent Judge

`PASS_PUX2A0_ELEMENT_SELECTION_CONTRACT_NO_EFFECT`

- deterministic inventory and digest: PASS;
- all required page owners and next identities: PASS;
- current incompleteness preserved: PASS;
- duplicate domain logic: 0;
- Developer2 overlap: 0;
- Provider/media/Human/Release/Deploy effect: 0.

This result enables P-UX-2A1 implementation planning. It does not authorize a
Provider call, credential use, paid execution, model acquisition/load,
generation, Candidate adoption, Timeline edit, Export, Release or Deploy.
