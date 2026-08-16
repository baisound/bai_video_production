# TASK-036 P-UX-2A — TASK-028 Connection Settings integration

Date: 2026-08-17

Unit: `TASK-036 / P-UX-2A`
State: `IMPLEMENTED_LOCAL / HOSTED_GATE_PENDING`

## Current checkpoint and ownership audit

- TASK-036 P-UX-1C is hosted-closed. Its V6.1.1 visual parity is preserved.
- TASK-037, 038, 039, 040, 042, 043, 044 and 045 are already hosted-closed;
  this unit does not recreate their Product truth.
- TASK-041 audio and the active TASK-046/TASK-047 voice/OBS route remain owned
  by Developer 2 and are unchanged.
- TASK-027 retains Planning/GO/Queue/adoption ownership. TASK-028 retains the
  canonical provider/model profile, store, preflight and editor contracts.
- The remaining non-overlapping gap was the TASK-036 Settings dialog: its
  `AIモデル` and `接続 / Secret` tabs were static even when an exact project
  `ai-connection-settings.json` already existed.

## Builder design

P-UX-2A composes the existing `ConnectionSettingsWebService` into the trusted
TASK-036 launch root only when the project contains a regular, non-symlink,
checksum-valid settings file. Absence remains an explicit unavailable state;
the Shell does not invent or copy a default profile.

The allowlisted bridge exposes only:

1. `connection_settings_snapshot` — a body-free form projection;
2. `connection_settings_update` — exact CAS update of all workload modes and
   optional preferred route IDs.

The bridge never accepts a path, endpoint, credential value, arbitrary catalog
entry, callback or executable. The update delegates validation and atomic CAS
storage to the existing TASK-028 implementation. It returns explicit
`provider_execution_started=false`, `paid_execution_authorized=false`,
`generation_started=false` and `credential_values_redisplayed=false` facts.

The V6.1.1 Settings UI renders the existing workload/route form using DOM
`textContent` construction. `AIモデル` may save mode and preferred-route
metadata. `接続 / Secret` displays configured/not-configured state only and
directs credential changes to the existing TASK-034 vault authority. It never
renders or collects a Secret.

## Deterministic and failure boundaries

- missing settings file: `available=false`, no implicit profile;
- symlink/non-file settings path: fail closed before Shell launch;
- invalid checksum/schema/profile: fail closed before Shell launch;
- stale revision: existing TASK-028 CAS conflict, no overwrite;
- missing/extra request fields: bridge validation error;
- unavailable bridge: state error on update;
- save success: settings metadata only, no Provider, paid, GO, generation,
  Candidate, media, Timeline, Resolve, Premiere, Release or Deploy effect.

## Verification

- TASK-036 Shell/launcher plus TASK-028 settings focused suite: `82 passed`;
- compileall: PASS;
- `git diff --check`: PASS;
- full repository regression is required before hosting.

## Builder / Completeness Critic

Finding: a second Settings parser/editor could diverge from TASK-028.

Resolution: the Shell receives `ConnectionSettingsWebService` and delegates
form creation, validation, CAS and persistence to the existing implementation.
Duplicate route-selection logic is zero.

Finding: an absent project profile could be silently replaced by the packaged
example.

Resolution: absence is rendered unavailable; no default is materialized.

Residual Critical/High/Medium: `0 / 0 / 0`.

## Security / Authority Critic

Finding: a Settings tab could become an implicit Provider or credential
execution surface.

Resolution: only mode/preferred-route metadata is mutable. Credential values,
catalog mutation, endpoint mutation and Provider dispatch are absent. Explicit
no-effect facts are returned and asserted.

Finding: a project-controlled symlink could redirect the trusted settings
write.

Resolution: the launch root rejects symlink and non-file coordinates before
binding the service; the existing store supplies atomic/CAS writes.

Residual Critical/High/Medium: `0 / 0 / 0`.

## Operations / Compatibility Critic

Finding: changing the launch configuration schema would invalidate existing
packaged configurations.

Resolution: no launch-config field is added. The already canonical project
filename is discovered only inside the exact trusted project root. Existing
projects without it retain the prior unavailable behavior.

Finding: P-UX-2 could disturb completed audio or NLE paths.

Resolution: audio, Timeline, Export, TASK-041 and TASK-044 code and behavior are
unchanged; the new bridge dependency is optional.

Residual Critical/High/Medium: `0 / 0 / 0`.

## Independent Judge

The implementation is a bounded composition of existing TASK-028 truth into
TASK-036. It closes the static-model-settings gap without reopening completed
TASK-037–045 domains or overlapping Developer 2's audio/voice/OBS files.

Provisional result: `PASS_LOCAL_PENDING_HOSTED_CHECKS`

Residual C/H/M: `0 / 0 / 0`.
