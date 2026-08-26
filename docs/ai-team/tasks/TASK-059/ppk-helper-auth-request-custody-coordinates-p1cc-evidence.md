# TASK-059 P1C-C — AUTH_REQUEST Custody Coordinates Evidence

Date: `2026-08-27`

Status: `PROTOCOL_CORRECTED_HELPER_RUNTIME_NEXT`

Development depth: `DEV-4 PRIVACY, AUTHORIZATION AND RELEASE INTEGRITY`

## Canonical correction

Pre-helper review found that the original `AUTH_REQUEST` schema transported P0
and P1A inputs but not the two parent-owned coordinates required to construct
P1B READY: Owner scope and the exact custody destination. A helper could not
lawfully call P1B without inventing an implicit store/path channel.

`AUTH_REQUEST`, already the sole secret-bearing frame, now contains one exact
`custody_request` object:

- canonical `owner_scope_sha256`; and
- bounded strict-UTF-8 `destination_path_utf8_b64` with NUL rejection.

The path remains confined to the anonymous pipe. It is not placed in argv,
environment, READY, receipts, errors, repr or Evidence. P1B continues to expose
only `destination_path_sha256`. Unknown/missing coordinates, invalid digest,
empty/base64-invalid/non-UTF-8/NUL path bodies fail with the fixed protocol
error.

Challenge, custody and receipt identities and bounded timestamps remain
helper-generated per attempt. The helper must still validate that the decoded
destination is an absolute path before P1B use.

## Verification

- corrected P1C wire plus P1C-B controller: `55 PASS`
- compile/strict canonical round-trip: `PASS`
- corrected wire/controller + P1A + P1B + canonical R9B: `92 PASS`
- real helper/process/PPK/passphrase/DPAPI/signing: `NOT EXECUTED`

## Critic / Judge

The correction removes the only missing P1B input without creating a second
store, path source or evidence channel. Destination plaintext remains within
the already secret-bearing request and fixed-error boundary.

Residual Critical/High/Medium/Low: `0 / 0 / 0 / 0`.

Decision: `GO` for P1C-C helper runtime implementation using synthetic secrets
and fake custody only.
