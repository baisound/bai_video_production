# TASK-059 P1C — Helper Process Wire Contract Evidence

Date: `2026-08-27`

Status: `WIRE_CONTRACT_IMPLEMENTED_LOCAL_PROCESS_CONTROLLER_NEXT`

Development depth: `DEV-4 PRIVACY, AUTHORIZATION AND RELEASE INTEGRITY`

## Implemented boundary

P1C now has a pure, synthetic-only anonymous-pipe wire contract. It implements
the fixed unsigned-big-endian 32-bit length prefix, canonical UTF-8 JSON,
`131072`-byte frame ceiling, eight-frame-per-direction ceiling, partial-read
assembly and exact frame schemas for `HELLO`, `HELLO_ACCEPTED`, `AUTH_REQUEST`,
`READY`, `CONFIRM`, `CANCEL`, `COMPLETED` and `FAILED`.

Duplicate keys, NaN/Infinity, BOM, invalid UTF-8, non-canonical JSON, unknown
fields, wrong versions, invalid nested canonical records, zero/oversized/
truncated/trailing frames and excessive JSON depth/field/list counts fail with
one fixed body-free protocol error. `AUTH_REQUEST` remains the sole
secret-bearing frame. Its PPK, RFC4716 public key and strict UTF-8 passphrase
bodies are bounded base64 fields and are never rendered in exceptions or
`repr`.

The parent-side state machine retains only body-free binding coordinates. It
binds outer session, READY hash/challenge/custody/key/Owner/destination,
confirmation hash, import receipt and canonical R9B custody receipt. Reordered,
replayed, cross-session or mixed receipts fail closed. Invalid reader input
zeroes the mutable buffer, including unconsumed bytes.

This unit imports no subprocess, filesystem, temporary-file, clipboard or
network capability. It does not authenticate a real PPK, start a helper,
perform DPAPI custody, sign, mutate a Knowledge Pack, release, deploy or activate
Production.

## Verification

- P1C focused synthetic contract: `39 PASS`
- P1C + P1A + P1B: `68 PASS`
- Windows 3.12 P1C + P1A + P1B + canonical R9B: `76 PASS`
- WSL P0 full, including oversized parser cases: `26 PASS`
- compileall: `PASS`
- real PPK/passphrase/DPAPI custody/signing: `NOT EXECUTED`

Windows pytest 9 cannot create temporary node-id paths for the two 64 KiB P0
parameter values. That runner limitation reproduced as `101 PASS / 2 setup
errors`; both cases and the complete P0 module passed under WSL. It is not a
Product failure and no case was omitted from final Evidence.

## Critic / Judge

Implementation Critic identified three pre-commit gaps: nested READY/CONFIRM/
COMPLETED coordinate mixing, retained reader bytes after invalid-frame decode,
and base64-valid but non-UTF-8 passphrase input. All three were corrected and
covered by negative tests.

Residual Critical/High/Medium/Low: `0 / 0 / 0 / 0`.

Decision: `GO` for local commit-ready P1C wire integration. The next Atomic Unit
may implement the short-lived no-console process controller/helper lifecycle
with synthetic secrets only. Operator UI and every real-key/native custody or
signing action remain separate Gates.
