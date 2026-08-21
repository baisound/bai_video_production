# P-UX-2G Native Local Image Provider Evidence

Date: 2026-08-21

Result: `PASS` for the bounded native Provider-port capability only

Product version: `0.22.0`

Source commit: `2aa53dfc4a516f5b9a1eb9cfffbbf41be7222580`

## Evidence boundary

This record proves one bounded native execution through the production
`LocalComfyTextToImagePort` using the local, free FLUX runtime. It is not an
end-to-end Product-flow completion record.

The operation used a synthetic prompt created only for this verification. It
did not use private user content. The following Product boundaries were not
exercised and remain unproven by this record:

- canonical TASK-027 Queue admission or Human GO;
- the trusted launcher or its runtime lease;
- the BAI VIDEO PRODUCTION Shell bridge;
- TASK-003 Asset or TASK-037 Candidate adoption;
- candidate ACCEPT or LOCK;
- Resolve, NLE, Final Review or Export;
- publication, deployment or release;
- any flow-completion token.

Accordingly, this Evidence must not be interpreted as
`TASK036_MOCK_ABSOLUTE_FUNCTIONAL_EXPORT_FLOW_COMPLETE` or as proof that all
application screens work through Export.

## Pre-dispatch verification

- ComfyUI version: `0.33.1`
- Runtime network binding: `127.0.0.1:8188`
- Metadata persistence disabled: `PASS`
- Required core node inventory: `PASS`
- Required checkpoint inventory: `flux1-schnell-fp8.safetensors`
- Production port preflight: `PASS`
- Preflight dispatch performed: `false`
- Preflight journal created: `false`
- Runtime identity and resource checks: `PASS`

## Native operation result

- Execution ID: `EXEC-NATIVE-FLUX-20260821-001`
- Provider operation ID: `bcde1a1c-4ee5-49dd-8fc2-15d2f8cddd16`
- Logical output reference:
  `project-output://generated/EXEC-NATIVE-FLUX-20260821-001/result.png`
- Media type: `IMAGE`
- Dimensions: `512x512`
- Output size: `267223` bytes
- Output SHA-256:
  `4134faae38851e623eab966d70ece861ce8d6f42c11edc37feb3c484ea5979bd`
- Provider latency: `293860 ms`
- Production PNG structural probe: `PASS`
- Prompt/workflow metadata markers in PNG: `ABSENT`
- Visual read-back: `PASS` (blue-hour coastal observatory/lighthouse scene)
- Provider dispatch count: `1`
- Paid Provider calls: `0`
- Cloud Provider calls: `0`
- Model downloads during the operation: `0`
- Automatic retry or duplicate dispatch: `0`

The exact journal and output bytes are preserved for read-only reconciliation.
Do not replay this logical execution under another evidence root.

## Safety disposition

A separate synthetic-Queue native runner was reviewed but did not pass the
required high-assurance security gate. It was not executed and was removed
before commit. Its result must not be combined with this Provider-port
Evidence.

The next eligible Product unit is a fresh, bounded design for canonical
TASK-027 Queue/Human GO through Shell execution and separate Asset adoption,
including durable two-phase state binding and parent-bound filesystem safety.
