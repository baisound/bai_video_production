# TASK-004 Live Behavioral Evidence — Attempt 06

- Date: 2026-08-09 (target run)
- Package: `0.4.5`
- Returned archive SHA-256: `4d777fdf1266031262353469a56223ff4722d93e79ffb9033807de6e3d3fde23`
- Result: `FAILED BEFORE AUDACITY MUTATION`
- Product error: `ERR_INPUT_SOURCE_CHANGED_DURING_INGEST`
- Error category: `DATA_INTEGRITY`

## Evidence review

The returned runtime database contains one Product operation only:

- command: `ASSET_INGEST`
- idempotency key: `task004-live-noise-source`
- status: `FAILED`
- created: `2026-08-09T01:39:41.201Z`
- updated: `2026-08-09T01:39:41.246Z`
- error: `ERR_INPUT_SOURCE_CHANGED_DURING_INGEST`

No Asset rows were committed and no Audacity/OpenVINO operation was dispatched. The generated synthetic source WAVs are present in the returned runtime. Therefore this attempt does **not** constitute an OpenVINO behavioral failure and must not be used to invalidate the already accepted capability Evidence.

## Corrective finding

TASK-003 ingest used `(size, mtime_ns)` equality before/after the streaming copy as its fast source-mutation guard. The target failure occurred on a freshly generated Windows WAV before external AI execution. Windows file last-write timestamps are not a sufficiently strong standalone content-identity signal: Microsoft documents that last-write values are not necessarily continuously updated and may be finalized according to filesystem/handle timing.

Package `0.4.6` keeps size drift as an immediate hard failure. If only `mtime_ns` drifts, the Product re-hashes the already-open source file handle and compares that complete second-pass checksum/size with the bytes that were staged. Content mismatch still fails `ERR_INPUT_SOURCE_CHANGED_DURING_INGEST`; timestamp-only drift with byte-identical content is accepted. The source path is not reopened during revalidation.

This correction strengthens the intended integrity property (content equality) while removing a Windows timestamp-only false positive. Behavioral Evidence must be rerun on package `0.4.6`.
