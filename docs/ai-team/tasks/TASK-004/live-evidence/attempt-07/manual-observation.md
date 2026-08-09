# TASK-004 Behavioral Evidence Attempt 07

- Returned package: `0.4.6`
- Evidence received: `2026-08-09`
- Result: **PRODUCT INGEST FAILED BEFORE AUDACITY MUTATION**
- Error: `ERR_INPUT_SOURCE_CHANGED_DURING_INGEST` / `DATA_INTEGRITY`
- Before size: `576044` bytes
- After size: `576044` bytes
- Copied size: `143` bytes
- Returned reason: `SIZE_CHANGED`

## Root-cause finding

The returned synthetic noise WAV is complete at `576044` bytes, while the Product copied exactly `143` bytes. The first byte with value `0x1A` (CTRL+Z) in that WAV is at zero-based offset `143`, exactly matching the copied byte count. On Windows, low-level CRT file descriptors opened without `O_BINARY` can use translated text mode, where CTRL+Z is interpreted as end-of-file on input. The TASK-003 ingest path used `os.open(..., O_RDONLY)` and raw `os.read`, so the synthetic binary media was truncated at the first CTRL+Z despite `fstat` reporting the full file size.

This is not source mutation and is not an OpenVINO behavioral failure. The operation database showed only the failed `ASSET_INGEST`; no Asset was published and no Audacity/OpenVINO effect was dispatched.

## Corrective contract for package 0.4.7

- Every low-level media source descriptor opened by Asset Ingest includes `os.O_BINARY` when the platform exposes it.
- The staging destination descriptor also includes `os.O_BINARY`, preventing LF/CRLF translation on arbitrary binary payloads.
- `O_NOFOLLOW` and the existing same-open-handle source-stability checks remain unchanged.
- Unix-like platforms use `getattr(os, "O_BINARY", 0)` and therefore retain existing flags.
- A regression test injects a Windows-style `O_BINARY` flag and verifies that both source and staging media descriptors receive it.

Primary platform references used during diagnosis: Python `os.open` documentation explicitly states that on Windows `O_BINARY` is needed for binary mode; Microsoft CRT translation-mode documentation states that text mode interprets CTRL+Z as EOF and `_O_BINARY` suppresses translation.

Behavioral Evidence must be rerun with package `0.4.7`; the previously accepted capability Evidence remains valid.
