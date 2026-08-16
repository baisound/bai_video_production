# TASK-036 P-UX-2A1 Model / Capability Selection Projection

Date: 2026-08-17  
Authority: `OWNER-AUTH-20260817-DEVELOPER1-EXCLUSIVE-ROADMAP-QUEUE-AUTONOMY-01`  
Checkpoint base: `d21e265cf8fad61180676a4386feeee5588eda38`  
State: `IMPLEMENTED_NO_EFFECT / REVIEW_CANDIDATE`

## Scope and ownership

This unit connects the existing TASK-028 Connection Settings route truth to the
Planning, Start/End Image, AI Video and Quick pages.  It also projects existing
TASK-040 compiled Prompt and TASK-042 Quick Intent route coordinates after a
Project is reopened.  It creates no second route, Prompt or Quick store.

Audio is excluded from this implementation.  TASK-041 and the Audio page remain
owned by Developer2.  Audio Quick Intent rows are counted as delegated but are
not exposed as mutable selectors by this unit.

## Contract

`Task036ModelSelectionProjection` accepts only the already secret-free TASK-028
form plus optional TASK-040/TASK-042 snapshots.  It emits:

- five Project-default selectors: Planning, Image, Video, Quick Image and Quick
  Video;
- exact persisted Scene/Prompt route bindings;
- exact persisted non-Audio Quick Intent route/capability bindings;
- deterministic canonical JSON and SHA-256;
- explicit `UNKNOWN_NOT_EVIDENCED` license/resource state and
  `NOT_AUTHORIZED` runtime state;
- permanent false values for Provider execution, paid authority and generation.

The Shell saves only the existing TASK-028 workload mode/preferred-route CAS
document.  It neither modifies compiled Prompt/Quick Intent receipts nor repairs
a missing or cross-workload binding.  Such bindings are surfaced as
`UNKNOWN_ROUTE` or `WORKLOAD_MISMATCH`.

## Bounds and fail-closed rules

- routes per workload: at most 64;
- Prompt bindings: at most 256;
- Quick Intent bindings: at most 256;
- duplicate workloads/routes, a preferred route outside its workload, malformed
  booleans, cap+1 and broad secret/effect fields reject;
- `api_key`, token/secret/password, credential/endpoint references, path, raw
  bytes, runner and callback surfaces reject;
- a configured route may be selected as metadata even when credential/runtime
  blockers are visible; selection never changes admission state;
- no filesystem, network, subprocess, Provider, model, media or native API is
  reachable from the projection.

## Checkpoint relationship to TASK-027/028/037–045

- TASK-028 supplies the only editable Project route preference.
- TASK-040 and TASK-042 supply immutable Scene/Quick bindings.
- TASK-027 and TASK-037–045 remain the downstream planning, Candidate, Prompt,
  Queue, persistence, NLE and release truth owners; their logic is not copied.
- TASK-041 Audio remains delegated to Developer2.
- TASK-037/038/039/040/042/043/044/045 are consumed as hosted-closed contracts,
  not reopened.

## Verification

- deterministic projection and canonical digest;
- Project/Scene/Quick coordinate projection;
- cross-workload mismatch and unknown-route visibility;
- secret/effect surface rejection;
- duplicate, malformed, bounds and cap+1 rejection;
- bridge unavailable/broad-request failure;
- existing TASK-028 update/reopen regression;
- main-page selector and no-effect text contract;
- P-UX-2A0 source inventory compatibility (`stable_ids` 106 -> 110 for the
  four named selector hosts; all other source counts unchanged);
- focused TASK-036 plus proportional full repository regression;
- `git diff --check` and exact changed-file review.

## Builder / Completeness Critic

Finding: a new selection store would fork canonical truth and make restart
reconciliation ambiguous.  Resolution: Project defaults delegate to TASK-028;
Scene/Quick coordinates are read-only projections of TASK-040/TASK-042.  Audio
is explicitly delegated.  Residual C/H/M: `0 / 0 / 0`.

## Security / Authority Critic

Finding: UI selection can be mistaken for execution, paid, license or resource
authority.  Resolution: the contract rejects secret/effect fields, never returns
credential references, makes license/resource UNKNOWN, and fixes execution,
paid and generation flags false.  Residual C/H/M: `0 / 0 / 0`.

## Operations / Compatibility Critic

Finding: existing Projects can have absent settings or stale Prompt/Quick route
coordinates.  Resolution: unbound settings are unavailable; persisted mismatches
remain visible and are never silently repaired.  Existing TASK-028 revision/CAS
is preserved.  Residual C/H/M: `0 / 0 / 0`.

## Independent Judge

`PASS_NO_EFFECT_PUX2A1_PROJECTION_PROVISIONAL`

The implementation is admissible for hosted review when focused/full tests,
hosted checks and exact changed-file review pass.  This decision does not grant
Provider, credential, download, model load, media, generation, Human approval,
Timeline, Release, Deploy or Production authority.
