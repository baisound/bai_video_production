# TASK-036 P-UX-2E E1 UI dispatch/read-back Evidence

Date: `2026-09-06 JST`

## Identity and authority

- Active Project: `ai-video-production`
- Active Task: `TASK-036 / P-UX-2E`
- Atomic Unit: `P-UX-2E-E1-UI-DISPATCH-READBACK-R1`
- Development depth: `DEV-4`
- Owner intent: close the remaining packaged-native functional-export route
  without reopening P-UX-1C or P-UX-2A0..D3 and without taking TASK-049/052/054
  responsibilities.
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
  -> trusted TASK-063 terminal package handoff
  -> separately authorized packaged Windows F0..F10 observation
  -> separately authorized native Export/TASK-011 byte + media QA read-back
  -> TASK036_MOCK_ABSOLUTE_FUNCTIONAL_EXPORT_FLOW_COMPLETE
```

The last four nodes are not completed or authorized by this Unit.

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

The existing visual system, layout, typography and navigation are unchanged.
The copy change is limited to clear Japanese action/result language.

## Verification

- Focused UI static + Node behavioral tests: `64 PASS`.
- Focused UI/backend dispatch/P0-E fixture/trusted-launcher regression:
  `115 PASS`.
- Changed Python compilation: `PASS`.
- `git diff --check`: `PASS`.
- Node negative coverage proves:
  - concurrent duplicate clicks admit one prepare/apply path;
  - rejected confirmation calls cancel and never apply;
  - an ambiguous apply followed by durable `DISPATCHING` read-back is not shown
    as success.

The first Windows attempt stopped at collection because the host runtime lacked
`jsonschema`. The first WSL attempt stopped at collection because its system
`cryptography` was older than the Product's declared `>=46` contract. These are
environment results, not Product failures. Final verification used an isolated
operation-owned WSL `/tmp` virtual environment with declared dependencies.

## Output roots and effects

- Build/package/install/runtime output root: `NONE`.
- Test roots: operation-owned `/tmp/bvp-task036-pux2e-*` directories only.
- External Provider, paid service, model download, private media, Resolve,
  renderer, Export artifact, installer, Release, Deploy and Production effects:
  `0`.
- Drive-root/direct-child task artifacts: `0`.
- Intentional residuals: isolated `/tmp` test environments may remain for OS
  cleanup; no Product/user state was written.
- External private checkpoint run: `20260906T094756+0900`; read-back identity
  and fields: `PASS`; SHA-256:
  `ed1459ba031828e63d6acf340e9dda66a83775cacb676fb8c48fdb8bb666d746`.

## Review and gate state

Builder self-review found no Critical/High/Medium issue in the bounded diff.
Independent DEV-4 Critic/Tester and hosted checks are `NOT_CONFIRMED`; therefore
the PR must remain Draft. Packaged EXE launch and native Export/output read-back
remain parked by `task063-l3-native-qa-runbook-2026-09-01.md`, whose current
state is `NOT_AUTHORIZED / DO_NOT_EXECUTE`.

This Unit does not mint `MOCK_ABSOLUTE_FUNCTIONAL_EXPORT_FLOW_PASS` or
`TASK036_MOCK_ABSOLUTE_FUNCTIONAL_EXPORT_FLOW_COMPLETE`.
