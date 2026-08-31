# TASK-065 PL-D lifecycle source matrix

State: `TASK_LOCAL_DESIGN_ACTIVE / SOURCE_START0 / EFFECT0`

Audit base: BVP `origin/main`
`35cdf1ad475633dcf035e0616e979b5a8fde0c88`.

The external task-local checkpoint
`2026-08-31-task065-pld-lifecycle-source-matrix.md` is read-only design input,
not canonical Evidence or a completion receipt. This repository-local matrix
records the admitted boundary without changing TASK-063, TASK-061, installer
source/state, SKILL source/config, or Production state.

## Effect-zero discovery boundary

The packaged installer CLI `discover` operation is not a read-only reader. Its
current call sequence is `discover_installed_bridge()` followed by
`write_installer_readback()`, and the historical test is accurately named
`test_discover_command_writes_only_the_fixed_installer_readback`. TASK-065
therefore must not invoke packaged `discover` during PL-A or PL-D admission.

The in-process `discover_installed_bridge(root)` is logically noncreating for
one caller-selected root, but it is not a Production-current selector until
TASK-063 closes same-open descriptor/owner/ancestor and strict-JSON
currentness. Current source has no authoritative active-install registry or
side-by-side selector. TASK-065 must not scan guessed roots or choose a
lexical, newest, first-found, or otherwise implicit winner.

PL-D requires both a trusted installer/Product current-registration receipt
and a corrected noncreating reader. Creation or replacement of
`installer-readback.json` is a lifecycle write, not an admissible discovery
side effect.

## Acceptance rows

| ID | Boundary | Historical regression input | Missing real/fault fixture or correction | Required result |
| --- | --- | --- | --- | --- |
| `PL65-D01` | effect-zero current-instance selection | caller-root logical discovery validates one descriptor/owner binding | trusted current-registration set; zero/one/multiple classifier; Product EXE/payload currentness; corrected noncreating reader; prove packaged `discover` call count zero | exactly one current tuple is only a candidate; zero/multiple/stale returns `STOP_PRESERVE / EFFECT0` |
| `PL65-D02` | custom Unicode/space/non-system root | custom Unicode root, exact installer-relative Bridge tree, opaque instance ID, no fabricated Profile, disabled receipt, fixed ProgramData literal zero | bind Product payload/EXE, installer receipt, same-open descriptor/owner identities, full ancestor chain and current registration; real long-path/non-system-drive execution | one instance-bound relative Bridge, public absolute path zero, `enabled:false`, no fallback |
| `PL65-D03` | same-root repair/upgrade continuity | same-root repair preserves instance/created time; logical safe readback update, tamper detection and selected rollback | secure lock; same-open generation; strict JSON; target/temp physical CAS; predecessor/current payload and registration chain; directory durability; foreign-replacement preservation | only exact predecessor/current continuity may retain instance identity; otherwise preserve and return stale/effect0 |
| `PL65-D04` | side-by-side/multiple installations | separate caller roots can mint separate UUIDs, but this is not active-install proof | canonical two-root fixture; trusted current-registration set; no root scan or implicit winner; no cross-instance config/Profile/receipt reuse | multiple current candidates return `MULTI_INSTALL_AMBIGUOUS / EFFECT0`; explicit installer/Human selection is separate |
| `PL65-D05` | uninstall preservation/stale root | installer source has no `[UninstallDelete]`; static tests preserve data intent | real install, bounded seed, uninstall and reopen; prove Product payload/registration removed, Bridge data preserved and descriptor no longer current; body-free receipt | `UNINSTALLED_DATA_PRESERVED / CONNECTOR_DISABLED / EFFECT0`; preserved Bridge is not current |
| `PL65-D06` | reinstall/moved/portable semantics | same-root valid descriptor can be reused logically | prove same-root predecessor continuity; different-root trusted rebind; removable/read-only/ACL/reparse/multi-host faults | valid same-root continuity may create a bounded successor; move/portable ambiguity requires rebind/effect0 and preserves old data |
| `PL65-D07` | lifecycle/config/activation coordination | disabled config/history candidate and Option B unchanged distribution config | TASK-061-B-owned trusted disable/history semantics and successor binding for upgrade/uninstall/instance drift | config/history must bind the current successor before use; mismatch is disabled/effect0; TASK-065 activation/history delta zero |
| `PL65-D08` | lifecycle rollback/unknown-state preservation | logical update/fresh rollback cases | crash seams across registration, payload, descriptor, owner, readback and config; exact-object rollback only; foreign replacement preserve | exact operation rollback may emit a bounded receipt; unknown state returns `STOP_PRESERVE`; unrelated overwrite/delete zero |
| `PL65-D09` | public-safe lifecycle closure receipt | disabled public discovery projection exposes only opaque instance/relative Bridge | bind lifecycle action, predecessor/successor Product registration/payload, descriptor/owner, config/history, preserved inventory, no-dual-write and executed status | future `TASK065_LIFECYCLE_CLOSURE_RECEIPT` is audit Evidence only, `authority_created:false`, body/path-free, and cannot activate or delete |

## Coverage separation

Historical tests remain reusable regression inputs for custom roots and exact
relative layout; same-root logical repair; descriptor tamper; fixed readback;
unsafe link/ancestor/target cases; logical update/rollback; selected installer
destination; reparse checks; absent `[UninstallDelete]`; and fixed ProgramData
literal zero. They do not prove real install, upgrade, uninstall, reinstall,
portable/rebind, multi-install selection, or Production currentness.

Missing closure fixtures include:

- zero/one/multiple trusted current registrations without root scanning;
- same bytes/different inode and descriptor/owner mixed-generation reads;
- Product EXE/payload and predecessor/current registration chains;
- real custom-root install, upgrade, uninstall, reinstall and preserved-data
  readback;
- portable/move/rebind, removable/read-only filesystem, ACL/reparse and
  multi-host concurrency faults;
- stale or cross-instance config, Profile, pointer and ticket rejection;
- every registration/payload/descriptor/owner/readback/config crash seam;
- foreign replacement preservation with delete/restore zero;
- body-free reason codes and absolute-root/account/OS-detail leakage zero; and
- exact Project/Bridge/SKILL/config/Profile before/after inventory deltas.

## Producer/consumer boundary

TASK-063 owns corrected installer-instance/current-registration and lifecycle
receipts. TASK-061-B owns trusted connector disable/history semantics.
TASK-065 PL-D consumes their durable receipts and verifies closure only. It
does not repair the installer, invoke effectful `discover`, scan roots, mutate
the distribution config, activate/deactivate, delete preserved data, or mint
missing upstream authority.

The future lifecycle receipt binds action/operation identity, trusted
Product/installer build and payload tree, predecessor/successor registration,
install instance and descriptor/owner physical identities, public relative
Bridge coordinate only, config/history predecessor/successor revisions,
body-free preserved inventory hashes/counts, exact mutation summary, and
executed/not-executed evidence identity. It always records
`authority_created:false`; `connector_enabled:false` remains required unless a
separate current Human Production Activation receipt exists.

## Gate

PL-D remains `START0 / EFFECT0` until
`TASK-068 -> {TASK-069,TASK-063} -> TASK-060 -> TASK-061-A -> TASK-067 -> TASK-036 -> TASK-061-B -> TASK-065`,
SKILL-D2S, TASK-065 source authority and separately authorized real Windows
lifecycle execution are all current. Static installer intent, file presence,
status, task-local probes and historical tests are not runtime PASS.
