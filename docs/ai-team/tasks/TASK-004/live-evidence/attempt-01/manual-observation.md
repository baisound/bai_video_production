# TASK-004 Target Runtime Attempt 01 — Manual Observation

Date: 2026-08-09
Status: PARTIAL LIVE EVIDENCE / NOT TASK COMPLETION

User-observed Windows target state:

- Audacity UI exposes OpenVINO Music Separation, OpenVINO Noise Suppression, and OpenVINO Super Resolution under `OpenVINO AI Effects`.
- PowerShell pipe enumeration returned both `ToSrvPipe` and `FromSrvPipe` while Audacity was running.
- The automated Audacity/OpenVINO capability worker nevertheless timed out at the original 15-second capability-discovery limit.
- The matching machine-generated timeout envelope is preserved as `audacity-openvino-capability.json`.

Interpretation:

- This observation is evidence that the plugin UI and named-pipe endpoints exist on the target machine.
- It is not equivalent to successful BAI command/reply capability discovery and does not authorize or prove any OpenVINO effect execution.
- Package 0.4.1 therefore changes only the capability-discovery supervision default/configuration and adds worker phase diagnostics; side-effecting audio execution remains separately controlled.
