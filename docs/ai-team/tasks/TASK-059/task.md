# TASK-059 — Owner Signing Key PPK Import Bridge

Status: `P1CC_AUTH_REQUEST_COORDINATES_CORRECTED_LOCAL_HELPER_RUNTIME_NEXT`

Authority: Owner exact instruction `続きを開発して` on `2026-08-26`, following
the requested TASK-029 BVP signing-key import procedure.

Development depth: `DEV-4 PRIVACY, AUTHORIZATION AND RELEASE INTEGRITY`

## Responsibility

TASK-059 owns the separately gated bridge from an Owner-held encrypted PuTTY
PPK Version 3 Ed25519 key to the existing TASK-029 R9B Owner-local DPAPI custody
boundary. It does not reopen or rewrite the hosted-closed TASK-029 R9B/R9C/R9D
history.

TASK-029 remains owner of:

- R9B one-shot raw 32-byte Ed25519 seed validation and Windows Current User
  DPAPI custody;
- R9C exact local signing and immediate R9A verification; and
- R9D durable signing journal semantics.

TASK-059 must not create a second custody store, signer registry, signing
protocol, Knowledge Pack store, promotion service or Product entrypoint.

## P0 checkpoint

P0 implements a pure, body-free encrypted-PPK public-coordinate preflight. It
strictly parses bounded PPK Version 3 metadata, requires Ed25519, AES-256-CBC and
Argon2id, validates bounded KDF metadata and encrypted private-block syntax, and
matches the PPK public blob against a separate RFC4716 public key and an exact
Owner-confirmed OpenSSH SHA-256 fingerprint.

The result exposes only digests, public fingerprint, KDF numeric metadata and
fixed false effect flags. It accepts no passphrase, performs no MAC verification
or private-key decryption, imports no custody, writes no file, starts no signing
and invokes no subprocess/network/DPAPI boundary. Fixed state is
`READY_FOR_PASSPHRASE_MAC_GATE_NO_CUSTODY_IMPORT`.

P0 synthetic Evidence is `26 PASS`; P0 plus direct R9A/R9B/R9C is `53 PASS,
1 intentional Windows DPAPI skip`; full TASK-029 plus TASK-059 regression is
`143 PASS, 4 intentional Windows DPAPI skips`. Schema/mirror, compileall, exact
admission and diff checks pass. No real PPK, private key, seed, passphrase or
Owner custody was read, created, imported, logged or persisted.

## P1 design checkpoint

P1 design is bound in
`ppk-import-secret-gate-p1-design-critic-judge.md`. It specifies a short-lived
Windows-only helper, anonymous-pipe secret transport, exact Argon2id/AES/HMAC
PPK v3 authentication, public-key rederivation, an in-session Owner confirmation
and exactly one call to the existing R9B provision/read-back boundary.

At the design checkpoint, P1 implementation remained a separate Human Gate.
The gate required exact allowed files, the pinned crypto/runtime compatibility
target and synthetic-only test scope before mutation.

Owner subsequently directed continued work without intermediate confirmation.
P1A now implements the internal synthetic-only secret-authentication core:
exact P0/file revalidation, bounded Argon2id 80-byte derivation, AES-256-CBC
decryption, constant-time PPK v3 HMAC verification, canonical Ed25519 mpint
normalization, public-key rederivation and one-shot helper-local seed access.

P1A performs no filesystem, process, UI, DPAPI, custody or signing effect. Its
Evidence is `14 PASS`; P0 remains `26 PASS`; P1A plus direct Windows
R9A/R9B/R9C regression is `42 PASS`.

P1B may add body-free READY/confirmation/receipt contracts and an in-memory
orchestrator over the existing R9B APIs using fake cipher/store tests only.
Windows process isolation, Operator UI and real DPAPI execution remain later
units.

Real PPK selection, passphrase entry, private-key decryption, DPAPI custody,
real signing, Knowledge Pack mutation/promotion, runtime apply, Release, Deploy
and Production remain separate Human Gates and are not authorized by P0.


## P1C wire checkpoint

The first P1C Atomic Unit implements the pure canonical wire codec, bounded
incremental reader and parent-side exact state machine. It permits one
secret-bearing `AUTH_REQUEST` frame only; every response and failure remains
body-free. READY, confirmation, import receipt and R9B custody receipt
coordinates are cross-bound, while replay, ordering drift, mixed receipts,
invalid UTF-8, non-canonical JSON and frame smuggling fail closed.

P1C focused Evidence is `39 PASS`; P1C + P1A + P1B is `68 PASS`; Windows
P1C/P1A/P1B/R9B direct regression is `76 PASS`; complete P0 including its two
oversized cases is `26 PASS` under WSL. Compileall passes. Detailed Evidence is
`ppk-helper-process-wire-p1c-evidence.md`.

The next bounded unit is the one-process-per-attempt, no-console,
shell-free controller/helper lifecycle with synthetic secrets only. Operator UI,
real PPK/passphrase, DPAPI custody, signing and public integration remain
separate Gates.


## P1C-B controller checkpoint

P1C-B adds the fixed, shell-free, no-console and one-use process controller.
Only anonymous stdin/stdout pipes carry canonical frames; stderr is DEVNULL and
the environment is allowlisted. Pipe direction, five-second header,
ten-second frame, five-minute attempt and bounded terminate/kill behavior fail
closed with fixed body-free errors. The parent's mutable encoded frame is
zeroed after every write attempt.

P1C-B focused Evidence is `15 PASS`; P1C-B plus wire is `54 PASS`; direct
P1C-B/wire/P1A/P1B/R9B regression is `91 PASS`; compileall passes. Detailed
Evidence is `ppk-helper-process-controller-p1cb-evidence.md`.

P1C-C next owns the fixed helper runtime composition and synthetic-only
P1A/P1B binding. No real helper was launched in P1C-B. Real PPK/passphrase,
DPAPI custody, signing, Operator UI and public integration remain separate
Gates.


## P1C-C helper contract correction

Pre-helper review found that P1B READY could not be constructed from the
original AUTH_REQUEST because Owner scope and custody destination were absent.
The sole secret-bearing frame now includes exact `custody_request` coordinates:
canonical Owner-scope digest and bounded strict-UTF-8 base64 destination path.
The path remains pipe-only and never appears in READY, receipt, error or
Evidence. Helper-generated identities and timestamps remain internal.

Corrected wire plus controller Evidence is `55 PASS`; direct P1A/P1B/R9B
regression is `92 PASS`; compile passes. Detailed Evidence is
`ppk-helper-auth-request-custody-coordinates-p1cc-evidence.md`. The fixed
helper runtime is next; real PPK/passphrase, DPAPI custody and signing remain
separate Gates.
