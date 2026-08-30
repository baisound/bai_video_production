# TASK-059 P1C-D - PPK Helper Runtime Evidence

Date: `2026-08-27`

Status: `LOCAL_IMPLEMENTATION_PASS_OPERATOR_GATE_NEXT`

Development depth: `DEV-4 PRIVACY, AUTHORIZATION AND RELEASE INTEGRITY`

## Atomic Unit boundary

P1C-D adds the fixed helper-side runtime for exactly one anonymous-pipe attempt.
The runtime composes only the already bounded TASK-059/TASK-029 responsibilities:

- P1C canonical length-framed wire and exact helper state machine;
- P1A encrypted PPK authentication and helper-local one-shot seed;
- P1B READY, explicit confirmation and custody-import orchestration; and
- TASK-029 R9B Owner-local custody store.

The production CLI accepts only `--protocol-version 1`. It writes no log,
uses no retry loop, emits no exception text and never carries a destination,
passphrase or private material in argv, environment, response or Evidence.
Dependency injection exists only to keep focused tests synthetic.

## Secret and custody boundaries

All decoded PPK, public-key, passphrase and destination buffers are mutable and
zeroed in `finally` blocks. An authenticated secret is cleared on CANCEL,
parent EOF after READY, authentication/custody failure and successful import.
The helper rejects an import adapter that returns without consuming the secret.

The custody-dispatched marker is set before the one permitted R9B call. Every
failure from that point through COMPLETED validation and pipe write is
conservatively reported as
`ERR_PPK_CUSTODY_RESULT_LOST_REQUIRES_READBACK` with exit code 4. It never
blindly retries an ambiguous custody result. Protocol failures before dispatch
remain the fixed protocol failure and carry no exception details.

## Verification

- Windows Python 3.12 compile: `PASS`
- P1C-D helper focused tests: `15 PASS`
- Windows P1C-D/P1C/P1B/P1A/P0/R9B direct regression, excluding the known
  Pytest 9 oversized-parameter-ID setup incompatibility: `129 PASS, 5 DESELECTED`
- The exact five excluded malformed/truncated/oversized P0 cases under existing
  WSL Pytest 7.4.4: `5 PASS`
- Secret-not-consumed, custody exception, invalid COMPLETED payload and
  COMPLETED pipe-write ambiguity all require read-back: `PASS`
- parent EOF after READY clears the authenticated secret: `PASS`

No real helper subprocess, real PPK/passphrase, DPAPI custody, signing, Product
Operator UI, installation, release, deploy or Production action was executed.
A packaged/native subprocess smoke remains `NOT_EXECUTED` until an installed
or frozen helper identity is available; source-layout execution would not prove
the fixed isolated controller command.

## Critic / Judge

Critic found two material fail-closed gaps during implementation review:

1. an injected custody adapter could return without consuming the secret; and
2. post-dispatch result construction, validation or output failure could be
   misclassified as a retryable-looking generic failure.

Both are corrected and covered by negative tests. The final diff keeps one
canonical custody owner, one attempt, fixed body-free failures and no new
authority.

Residual Critical/High/Medium/Low: `0 / 0 / 0 / 0`.

Decision: `GO` for the next bounded parent/Operator integration unit using
synthetic fixtures. Real key import, DPAPI custody and signing remain separate
Human Gates.
