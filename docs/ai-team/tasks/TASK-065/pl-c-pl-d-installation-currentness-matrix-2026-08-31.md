# TASK-065 PL-C to PL-D installation currentness matrix

State: `TASK_LOCAL_SOURCE_BACKED_REFINEMENT / SOURCE_START0 / EFFECT0`

Source baseline: BVP `origin/main`
`35cdf1ad475633dcf035e0616e979b5a8fde0c88`.

The external checkpoint is read-only design input, not completion Evidence.
This matrix preserves one installed Product generation through TASK-036,
PL-C, TASK-061-B and PL-D without executing the adapter or changing source,
config, installer, Profile, learning data or Production.

## Currentness chain

```text
TASK-063 current-installation/lifecycle receipt
 -> PL-A candidate snapshot
 -> PL-B immutable config/ticket
 -> TASK-036 installed invocation/E2E receipt
 -> public receipt + hidden correlation + canonical/Profile readback
 -> PL65-C01a effect-zero join
 -> TASK-061-B final CA-C (enabled:false)
 -> separate Human Activation Gate
 -> PL65-C01b fresh post-activation operation
 -> PL-D trusted lifecycle successor closure
```

Every arrow binds the same installation generation unless an explicit trusted
lifecycle successor is journaled. `executed:true`, adapter build or hash
equality without physical/current registration proof is insufficient.

## Receipt propagation

| Stage | Minimum private binding | Public ceiling |
| --- | --- | --- |
| TASK-036 operation | installation/set/selected-registration, Product build/payload, lifecycle, config projection, ticket/consume and start/end currentness | opaque operation/build/config/install hashes, true execution and counts; no path/body |
| TASK-036 packaged EXE | frozen `spec -> windows_entry -> packaged_main` chain, Montage entry/module payload-tree, internally resolved installed EXE, private dispatch exact1 before probe/guard/shell/presenter call0 and installer/discover call0 | opaque build/payload/EXE/dispatch hashes and counts; `authority_created:false`; no path/body/correlation |
| TASK-036 E2E | operation bindings plus request/delivery, strict public receipt, hidden correlation, canonical and Profile readbacks | bounded status/reasons/opaque hashes; hidden body private |
| PL65-C01a | freshly pinned current installation/lifecycle plus exact E2E chain; historical stage/import each 1; local calls 0 | `PREACTIVATION_E2E_ADMITTED`; authority false |
| TASK-061-B | same installation/config/source/E2E/Profile currentness; operation-specific immutable terminal receipt and trusted exact coordinate; enabled remains false | body-free CA-C completion; Activation false; fixed history tail/caller time/revision/reconstructed receipt authority0 |
| PL65-C01b | fresh installation/lifecycle, separate Human receipt, new operation/ticket/config/delivery/E2E | explicitly post-activation; no C01a substitution |
| PL-D | predecessor/successor registration/payload/descriptor/owner/config/history plus preserved inventory/no-dual-write | audit-only closure, `authority_created:false`, no delete/activation |

TASK-036 checks immediately before launch and at terminal capture. C01a and
TASK-061-B freshly join current registration/lifecycle rather than trusting an
old timestamp. C01b takes a new snapshot and authority. PL-D observes trusted
successors only and performs no repair, deletion, discovery or activation.
Packaged `discover`, installer-readback writes and root scans remain zero at
every TASK-065 read-only admission/closure stage.

Static packaging tests, `console=False`, stdout silence, exit0 and EXE presence
do not establish the packaged-EXE row. TASK-063's installed private-command
launch/wait followed by exit0+`FileExists` is also existence-only. The row
requires the T36-P01-P14 frozen
inclusion and real-installed execution receipt defined in
`task036-packaged-exe-chain-admission-2026-08-31.md`.

## PLC-I01-I16

| ID | Fault | Required result |
| --- | --- | --- |
| `PLC-I01` | executed TASK-036 receipt lacks installation/lifecycle | C01a reject; runtime PASS 0 |
| `PLC-I02` | upgrade after E2E before C01a | predecessor E2E stale; successor operation required |
| `PLC-I03` | uninstall after E2E with preserved Bridge | preserved/disabled; C01a/C01b 0; no delete |
| `PLC-I04` | second current installation before C01a | ambiguous; no winner/config/adapter effect |
| `PLC-I05` | same instance hashes but Product build/payload changes | reject mixed generation |
| `PLC-I06` | registration/lifecycle belongs to other root/build/instance | cross-install reject; path/body 0 |
| `PLC-I07` | TASK-061-B names other config/install generation | closure 0; config/history unchanged |
| `PLC-I08` | C01a receipt substituted for C01b | PL65-C02 reject; command 0 |
| `PLC-I09` | C01b receipt substituted backward for C01a | reject; no retroactive admission |
| `PLC-I10` | Human receipt belongs to predecessor lifecycle | activation/post-activation 0; fresh Gate |
| `PLC-I11` | PL-D omits E2E/config predecessor chain | reject closure; preserve state |
| `PLC-I12` | lifecycle successor during C01a/C01b join | burn old capability; no retry/winner recompute |
| `PLC-I13` | status/exit/public receipt lacks correlation/Profile | runtime/admission PASS 0 |
| `PLC-I14` | second publish confirms terminal admission | reject; delivery recreation 0; trusted readback only |
| `PLC-I15` | packaged `discover` refreshes C/D stage | prohibited call assertion fails; no receipt |
| `PLC-I16` | public output leaks root/EXE/SID/account/OS/body/correlation | public receipt 0; body-free failure |
| `PLC-I17` | TASK-061-B duplicate is inferred from fixed history tail or reconstructed receipt | C01a/PL-D reject; `DUPLICATE_CURRENTNESS_AUTHORITY_NOT_CREATED`; all local deltas 0 |
| `PLC-I18` | exact duplicate after later unrelated event, stale/wrong terminal coordinate, or same evidence with different action/body | collision/currentness reject; no implicit newest/tail winner; config/history delta0 |
| `PLC-I19` | terminal receipt swap/hardlink/reparse, concurrent same ticket, or crash across terminal publish/head transition | only exact pinned operation terminal may recover; one Product event exact0/1, second effect0, unrelated overwrite/delete0 |

Each case records Product/Project inventory, exact Bridge correlation/receipt/
pending delta, config/history/Profile delta, adapter/TASK-036/installer counts,
registration cardinality, predecessor/successor hashes and leakage count.

PL-C and PL-D remain `START0 / EFFECT0` until
`A61B-IMMUTABLE-DUPLICATE-TERMINAL` and the rest of TASK-061-B are complete. A once-valid or executed receipt is
not current by itself; current installed generation remains bound end to end.
