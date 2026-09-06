# TASK-036 P-UX-2E E1 UI dispatch/read-back Evidence

Date: `2026-09-06 JST`

## Identity and authority

- Active Project: `ai-video-production`
- Active Task: `TASK-036 / P-UX-2E`
- Atomic Unit: `P-UX-2E-E1-UI-DISPATCH-READBACK-R1`
- Development depth: `DEV-4`
- Owner intent: integrate the E1 source checkpoint without waiting for the
  separately gated packaged-native E2 observation, without reopening P-UX-1C
  or P-UX-2A0..D3 and without taking TASK-049/052/054 responsibilities.
- Base/current `origin/main`: `d97a0049b8beab54ad8121ed611eab6621d9690e`
- Branch: `codex/task-036-pux2e-ui-dispatch-readback-r1`
- Worktree: dedicated Codex worktree; exact local coordinate is retained only in
  the external private checkpoint.

## Fresh-main, PR and lock audit

- The worktree began detached and clean at the exact fresh `origin/main` above.
- The only open PR observed was Draft PR `#525` for TASK-069. It has no overlap
  with this Unit.
- `ACTIVE-WORK-LOCKS.json` revision `139` had zero nonclosed locks. Historical
  TASK-036 worktrees and branches were treated as foreign/no-touch.
- No current-state, roadmap, CHANGELOG, shared-lock registry, release or CI file
  is changed by this Unit.

## Bounded dependency DAG

```text
canonical P-UX-2A0..D5 + existing E1 backend dispatch contracts
  -> E1 UI single-flight / explicit confirmation / durable Job read-back (this Unit)
  -> independent DEV-4 review + hosted checks
  -> E1 source checkpoint merge

separate P-UX-2E-E2-PACKAGED-NATIVE-OBSERVATION
  -> exact E1 merge receipt
  -> trusted TASK-063 terminal package handoff + helper identity
  -> separately authorized packaged Windows F0..F10 observation
  -> separately authorized native Export/TASK-011 byte + media QA read-back
  -> only then evaluate TASK036_MOCK_ABSOLUTE_FUNCTIONAL_EXPORT_FLOW_COMPLETE
```

The E2 branch is not completed or authorized by this Unit. E1 source merge does
not wait for E2, and this PR must not be held open for packaged-native evidence.

## Allowed Files used

- `src/ai_video_production/task036_shell_v611.py`
- `tests/test_task036_v611_visual_contract.py`
- `tests/test_task036_v611_interaction_contract.py`
- this Evidence record

All other Product, DbD, Voice, Dataset/training, installer, shared governance and
release paths are read-only or denied.

## Implementation result

- The existing per-Job Export action now has a browser-local single-flight guard
  keyed by durable Job ID.
- Rejecting the final prompt consumes the prepared confirmation and never calls
  dispatch.
- Accepting the final prompt invokes the existing private Shell dispatch only
  once, then reads the durable Export Queue again.
- User-visible result text is derived from the exact durable Job stage and
  public-safe `evidence_ref`; a transient apply response can no longer mint a
  success message.
- Missing/ambiguous read-back remains `UNKNOWN` or `未確認`; no automatic replay,
  host path, raw exception, renderer, destination or authority is exposed.
- Export RPC failures use fixed public-safe Japanese copy; path-bearing bridge
  exceptions are never reflected into the browser notification.
- A rejected dispatch is reported as cancelled only when the receipt exactly
  matches `cancelled`, Job ID, confirmation ID and `external_mutation_started`.
  Missing or mismatched receipts remain `取消結果を確認できません`.

The existing visual system, layout, typography and navigation are unchanged.
The copy change is limited to clear Japanese action/result language.

## Verification

- Builder focused UI static + Node behavioral tests: `65 PASS`.
- Focused UI/backend dispatch/P0-E fixture/trusted-launcher regression:
  `116 PASS in 57.36s`.
- Changed Python compilation: `PASS`.
- `git diff --check`: `PASS`.
- Node negative coverage proves:
  - concurrent duplicate clicks admit one prepare/apply path;
  - rejected confirmation calls cancel and never apply;
  - a null or mismatched cancel receipt never mints cancellation success;
  - path-bearing prepare/apply/snapshot rejection uses public-safe copy only;
  - an ambiguous apply followed by durable `DISPATCHING` read-back is not shown
    as success.

Independent fix-delta Tester verification passed the two-file UI suite with
`65 PASS in 5.29s` and an implementation-extracted `15 scenarios PASS`, covering
private-path rejection, exact and mismatched cancellation receipts, missing or
wrong-Job snapshots, all displayed stages, duplicate clicks, guard release and
no automatic replay.

The first Windows attempt stopped at collection because the host runtime lacked
`jsonschema`. The first WSL attempt stopped at collection because its system
`cryptography` was older than the Product's declared `>=46` contract. These are
environment results, not Product failures. Final verification used an isolated
operation-owned WSL `/tmp` virtual environment with declared dependencies.

## Output roots and effects

- Build/package/install/runtime output root: `NONE`.
- Test root: operation-owned
  `/tmp/bvp-task036-pux2e-dev4fix-20260906T101500Z-ae43a3`; its isolated venv
  used cached declared dependencies and was absent on read-back after WSL exit.
- Compilation pycache root:
  `C:\Users\user\AppData\Local\Temp\bvp-task036-pux2e-dev4fix-20260906T102300-ae43a3`;
  exact containment/identity cleanup: `PASS`; residual: `NONE`.
- External Provider, paid service, model download, private media, Resolve,
  renderer, Export artifact, installer, Release, Deploy and Production effects:
  `0`.
- Drive-root/direct-child task artifacts: `0`.
- Intentional residuals: `NONE`; no Product/user state was written.
- External private checkpoint run: `20260906T094756+0900`; read-back identity
  and fields: `PASS`; SHA-256:
  `ed1459ba031828e63d6acf340e9dda66a83775cacb676fb8c48fdb8bb666d746`.

## Review and gate state

Independent review of committed head
`242bc3d9743e498741335b8ce5609dcde869f769` initially found
`Critical/High/Medium/Low = 0/1/1/0`: raw Export RPC exceptions could expose a
private host path, and an unconfirmed cancel result could overwrite the error
with success copy. Both findings were corrected and covered by negative tests.

- Independent Critic fix-delta result: `PASS`, unresolved `0/0/0/0`.
- Independent Tester fix-delta result: `PASS`, unresolved `0/0/0/0`.
- Independent Judge result: code candidate and E1 source-merge boundary `PASS`,
  unresolved `0/0/0/0`, completion markers not generated.

The old committed head's hosted checks were eight `SUCCESS` and one metadata
failure: `changelog-and-version` requires a shared `CHANGELOG.md` update. They
are not reused as final-head Evidence. The final exact source head and its new
hosted results are recorded in the external Evidence run after commit/read-back.
The PR remains Draft/HOLD until that freeze and the metadata sole-writer's
fresh shared-lock/overlap check and CHANGELOG update.

Packaged EXE launch, TASK-063 handoff/helper consumption, F0..F10 observation,
native Export/TASK-011 QA and Resolve effects remain `NOT_EXECUTED /
NOT_CONFIRMED`, parked for the separate
`P-UX-2E-E2-PACKAGED-NATIVE-OBSERVATION` checkpoint.

This Unit does not mint `MOCK_ABSOLUTE_FUNCTIONAL_EXPORT_FLOW_PASS` or
`TASK036_MOCK_ABSOLUTE_FUNCTIONAL_EXPORT_FLOW_COMPLETE`.
