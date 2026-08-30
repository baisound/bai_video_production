# TASK-059 P1C-B — Helper Process Controller Evidence

Date: `2026-08-27`

Status: `CONTROLLER_IMPLEMENTED_LOCAL_HELPER_RUNTIME_NEXT`

Development depth: `DEV-4 PRIVACY, AUTHORIZATION AND RELEASE INTEGRITY`

## Implemented boundary

P1C-B adds the one-process-per-attempt parent controller around the existing
P1C wire contract. The command is fixed to the selected executable plus
isolated/unbuffered module launch and protocol version. No caller-supplied
arguments are admitted. The environment reuses the Product's minimal worker
allowlist; API keys, passwords and unrelated variables are removed.

The launch is shell-free and uses only `stdin=PIPE`, `stdout=PIPE` and
`stderr=DEVNULL`, with inherited descriptors closed and Windows
`CREATE_NO_WINDOW`. Header, frame, whole-attempt and stop ceilings are fixed at
5 seconds, 10 seconds, 5 minutes and 2 seconds respectively. Timeout, EOF,
invalid length/body, wrong pipe direction, early/nonzero exit and I/O failure
produce fixed body-free errors and terminate the child. Terminate has one
bounded kill fallback.

Only `HELLO`, `AUTH_REQUEST`, `CONFIRM` and `CANCEL` may travel parent-to-helper;
only `HELLO_ACCEPTED`, `READY`, `COMPLETED` and `FAILED` may return. The mutable
encoded parent frame is zeroed in `finally`, including timeout and failure. A
controller cannot launch a second helper after finish or abort.

P1C-B does not implement the helper module, invoke P1A/P1B, read files, perform
PPK authentication, call DPAPI, sign, mutate a Knowledge Pack or expose an
Operator UI. Tests used fake processes and synthetic payloads only; no real
subprocess was launched.

## Verification

- P1C-B focused fake-process controller: `15 PASS`
- P1C-B + P1C wire: `54 PASS`
- P1C-B + wire + P1A + P1B + canonical R9B: `91 PASS`
- compileall: `PASS`
- real helper/process/PPK/passphrase/DPAPI/signing: `NOT EXECUTED`

## Critic / Judge

Implementation Critic required parent-frame mutable zeroization, strict pipe
direction, non-finite timeout rejection, fixed wait-failure mapping and
one-controller/one-helper reuse prevention. Each item is implemented and has a
negative test.

Residual Critical/High/Medium/Low: `0 / 0 / 0 / 0`.

Decision: `GO` for local P1C-B commit-ready integration. P1C-C may implement
the fixed helper runtime and bind its state machine to P1A/P1B using synthetic
secrets and fake custody only. Real Owner-key use and Operator UI remain
separate Gates.
