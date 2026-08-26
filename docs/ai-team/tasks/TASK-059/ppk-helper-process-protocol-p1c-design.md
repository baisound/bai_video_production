# TASK-059 P1C — Short-lived Helper Process Protocol Design

Date: `2026-08-26`

Status: `DESIGN_BOUND_IMPLEMENTATION_NEXT`

Development depth: `DEV-4 PRIVACY, AUTHORIZATION AND RELEASE INTEGRITY`

## Boundary

P1C owns only the anonymous-pipe wire contract and short-lived helper process
lifecycle around implemented P1A/P1B. It does not own cryptography, R9B custody,
signing, Knowledge Pack mutation, Release, Deploy or Production.

The existing no-console worker pattern is reused for `shell=False`, sanitized
environment, hidden Windows process and bounded terminate/kill. P1C differs by
allowing only explicit `stdin=PIPE`, `stdout=PIPE`, `stderr=DEVNULL`; no other
inherited handles are allowed.

## Launch contract

- argv contains executable/module identity and one non-secret protocol version;
- argv/environment never contains a path, fingerprint, PPK, passphrase, seed,
  custody identity, receipt or nonce;
- no shell, console, temp file, clipboard, inherited current input or log file;
- parent creates one helper per attempt and never reuses it;
- parent closes its passphrase buffer immediately after the secret frame write;
- helper termination is the authoritative secret-memory reclamation boundary.

## Frame format

Each direction uses exactly:

```text
uint32_be payload_length
payload_length bytes canonical UTF-8 JSON
```

Limits:

- maximum frame: `131072` bytes;
- maximum frames per direction: `8`;
- header read timeout: `5` seconds;
- non-KDF frame completion timeout: `10` seconds;
- whole attempt timeout: `5` minutes;
- duplicate, zero, oversized, truncated or trailing frames terminate the helper.

JSON is canonical, object-only, duplicate-key rejecting and schema/version
exact. Unknown fields, NaN/Infinity, BOM and non-UTF-8 fail closed.

## State machine

```text
SPAWNED
  parent -> HELLO(version, session_id, non-secret capability coordinates)
  helper -> HELLO_ACCEPTED
  parent -> AUTH_REQUEST(P0 payload, PPK/public bodies, passphrase body)
  helper -> READY(P1B body-free READY payload)
  parent -> CONFIRM(P1B exact confirmation) | CANCEL
  helper -> COMPLETED(P1B + R9B body-free receipts) | FAILED(fixed code)
  helper -> EXIT
```

`AUTH_REQUEST` is the only secret-bearing frame. Its canonical JSON bytes are
never logged, hashed into Evidence, echoed or included in exceptions. PPK and
public bodies are base64 inside this one pipe frame; passphrase is base64 of the
strict UTF-8 mutable buffer. The helper decodes once, clears mutable decoded
buffers best-effort and never returns a request coordinate derived only from
the passphrase.

READY contains only the implemented P1B body-free record. CONFIRM must reproduce
its exact session/challenge/hash coordinates. EOF, CANCEL, timeout, mismatch or
parent death clears state and exits without R9B mutation.

## Failure protocol

Public failures contain only protocol version, session ID, fixed error code,
phase and retryable=false. Secret-auth failures collapse to
`ERR_PPK_SECRET_AUTHENTICATION_FAILED`. No exception class/message, path,
crypto parameter, byte count beyond public frame ceilings or decrypted state is
returned.

After any possible R9B success, response loss is recovered only through a new
non-secret canonical custody read-back flow; the helper never reprovisions.

## Required tests

- canonical frame encode/decode and partial-read assembly;
- zero/oversize/truncated/duplicate/trailing/unknown frame rejection;
- duplicate JSON key, invalid UTF-8, NaN/Infinity and depth/field ceilings;
- secret substring absence from argv/env/stderr/error/result;
- PPK/passphrase buffer clearing on success, failure, Cancel and timeout;
- strict state ordering and one AUTH_REQUEST/CONFIRM maximum;
- EOF/parent death/terminate/kill cleanup;
- fake P1A/P1B success and fixed error mapping;
- no automatic custody retry after response loss;
- Windows no-console process smoke with synthetic secret only.

## Critic / Judge

- Critical: generic JSON subprocess protocols can echo secrets. Resolved by one
  secret-bearing request type, fixed body-free responses and DEVNULL stderr.
- Critical: helper reuse retains key material. Resolved by one process/attempt.
- High: argv/env/temp transport leaks. Resolved by anonymous pipe only.
- High: frame smuggling or replay mutates state. Resolved by exact state machine,
  frame counts, nonce binding, canonical JSON and fail-closed termination.
- High: parent death leaves a secret worker. Resolved by pipe EOF plus bounded
  parent controller terminate/kill.
- Medium: diagnostic error detail becomes an oracle. Resolved by fixed codes.

Residual Critical/High/Medium/Low: `0 / 0 / 0 / 0` for design.

Decision: `GO` for synthetic-only P1C wire/lifecycle implementation. Real PPK,
passphrase, DPAPI custody, signing and public Push remain separately gated.
