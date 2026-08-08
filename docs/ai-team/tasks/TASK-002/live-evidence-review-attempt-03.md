# TASK-002 — Live Evidence Review Attempt 03

## Decision

`ACCEPTED_FOR_TASK_COMPLETION`

## Evidence intake

Owner-returned archive: `resolve-spike-evidence (2).zip`.

Historical originals are preserved under `evidence/windows-live-attempt-03/` with SHA-256 intake hashes. Original JSON payloads were not rewritten.

## Target Resolve behavioral result

- Host: Windows 11 / Python 3.12.4
- Product: DaVinci Resolve Studio 21.0.2.4
- Resolve bridge: `WINDOWS_PROGRAMDATA`
- Mode: `SANDBOX_MUTATION`
- Sandbox Project: `BAI_CAPABILITY_PROBE_MANUAL`
- Mutation authorization: true
- Mutation execution: true
- Final matrix: `15 SUPPORTED / 1 LIMITED / 7 PROBE_REQUIRED / 0 UNSUPPORTED`

Behaviorally measured as SUPPORTED in the isolated sandbox include Project load/save/export, Media Pool access, Bin creation, generated WAV import, Timeline creation, Timeline append and marker placement. `project.create` is LIMITED only because the Owner manually created and opened the named sandbox before the successful run; creation was intentionally not repeated.

The remaining seven `PROBE_REQUIRED` capabilities are intentionally outside this spike's destructive/side-effect envelope: relink, subtitle mutation and render configuration/submit/start/status/cancel. Their unresolved state is not converted to UNSUPPORTED.

## WSL2 -> Windows IPC result

- Candidate: `LOCALHOST_HTTP_JSON`
- Endpoint host kind: `DEFAULT_GATEWAY`
- auth rejection verified: PASS
- authenticated roundtrip verified: PASS
- same-endpoint restart verified: PASS
- round trips: 16
- latency p50: `1.255 ms`
- latency p95: `1.699 ms`
- bearer token persisted in Evidence: false

This satisfies the target-topology IPC gate.

## Operator post-run observation

The Owner observed that the imported one-second probe WAV appeared online immediately after execution and became red/offline a few seconds after the process ended. Code review traced this to package 0.2.3 using `TemporaryDirectory` for the imported WAV and exported DRP; the directory was removed at process exit.

Package 0.2.4 retains those probe assets under the Evidence directory and constrains Sandbox Project names to a path-safe grammar. This correction is locally regression-tested. Per explicit Owner direction, a second live run solely to visually confirm that the retained media remains online is **not** a TASK-002 completion requirement.

## Conclusion

The capability and IPC gates required by TASK-002 are satisfied. The post-run media-offline behavior is a harness cleanup defect, not a failure of Resolve media import or Timeline placement capability, and is corrected before final completion.
