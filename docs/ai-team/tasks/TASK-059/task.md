# TASK-059 — Owner Signing Key PPK Import Bridge

Status: `P1CG2_PACKAGING_NATIVE_PASS_NATIVE_OPERATOR_ADAPTER_NEXT`

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

## P1C-D helper runtime checkpoint

P1C-D composes the fixed one-attempt helper runtime over the existing P1C wire,
P1A authentication, P1B confirmation/import orchestration and TASK-029 R9B
custody owner. The exact CLI accepts only `--protocol-version 1`; every
secret-bearing input remains anonymous-pipe-only and decoded mutable buffers
are zeroed.

CANCEL and parent EOF after READY clear the authenticated secret without
custody. After the sole custody dispatch begins, every exception, invalid
COMPLETED payload or output loss becomes
`ERR_PPK_CUSTODY_RESULT_LOST_REQUIRES_READBACK`; no blind retry is permitted.
The helper also rejects a custody adapter that returns without consuming the
secret.

P1C-D focused Evidence is `15 PASS`. Direct Windows regression is `129 PASS,
5 DESELECTED` only for the known Pytest 9 oversized-parameter-ID setup issue;
the exact five excluded cases are `5 PASS` under WSL. Compile passes.
Detailed Evidence is `ppk-helper-runtime-p1cd-evidence.md`.

The next bounded unit is parent/Operator integration with synthetic fixtures.
Real PPK/passphrase, DPAPI custody, signing and public integration remain
separate Human Gates.

## P1C-E parent Operator Session checkpoint

P1C-E adds the transient one-use parent Session over P1C-B. It transfers the
secret-bearing AUTH_REQUEST without retaining it, clears all transferred
mutable buffers on success and failure, and exposes only a destination-redacted
repr of the Japanese READY projection.

The parent re-admits P0 and independently cross-binds READY to the preflight
hash, PPK hash, signer ID, fingerprint, Owner scope and canonical destination
hash. Explicit confirmation is compiled from current READY only; false
confirmation sends nothing and Cancel remains available. Helper failure codes,
including custody-result-lost/read-back-required, remain terminal and never
trigger an automatic retry.

P1C-E focused Evidence is `10 PASS`; P1C-E plus direct P1C-D/P1C-B/P1C/P1B/
P1A/R9B regression is `117 PASS`; compile passes. Detailed Evidence is
`ppk-parent-operator-session-p1ce-evidence.md`.


The next bounded unit is synthetic-only Tk Operator wiring. Real PPK selection,
passphrase entry, helper launch, DPAPI custody and signing remain separate Human
Gates.

## P1C-F canonical Operator UI route

Canonical entrypoint review supersedes the provisional `Tk UI next` routing
label without rewriting P1C-E Evidence. The import flow belongs in the unified
`BAI Video Production.exe` Settings `Connection / Secret` card. A native
local dialog is only an adapter for file selection and masked passphrase input;
it is not a second Product or Settings route.

Passphrase input must never cross WebView JavaScript or JSON RPC. File paths and
bodies remain Python-local; Shell snapshots receive opaque candidate IDs and
body-free coordinates only. READY/Confirm/Cancel reuse the P1C-E one-use
Session, and custody-result loss exposes read-back recovery with retry disabled.

Review also found that P1C-B currently launches only a development Python
module. A frozen unified Product cannot use that argv as its packaged helper
identity. P1C-G must therefore implement the exact adjacent packaged-helper
identity/command before any UI action is enabled. Detailed design and
Critic/Judge decision are in
`ppk-canonical-operator-ui-route-p1cf-design.md`.

## P1C-G1 packaged helper identity checkpoint

P1C-G1 separates the existing development Python-module launch from one exact
packaged-helper launch variant. The packaged variant requires an absolute
`BAI Video Production Key Helper.exe` path, a lowercase pinned SHA-256
coordinate and the fixed `--protocol-version 1` argv. It never falls back to
PATH or accepts caller-supplied extra arguments.

Immediately before process creation, the controller rejects a symlink,
non-regular file, empty file, file above the 128 MiB bound, unstable file
metadata or digest mismatch. The verified file handle remains open across the
process-creation call, and packaged mode is admitted only on Windows. Admission
failure consumes the one-use controller and returns the body-free
`ERR_PPK_HELPER_IDENTITY_MISMATCH` code.

P1C-G1 focused Evidence is `21 PASS`; P1C-G1 plus direct P1C-E/P1C-D/P1C-B/
wire/P1B/P1A/R9B regression is `123 PASS`; compile passes. Detailed Evidence
is `ppk-packaged-helper-identity-p1cg1-evidence.md`.

P1C-G1 does not build, install, sign or launch a real packaged helper. The
trusted digest source, exact adjacency to the unified Product, packaging
composition, installation ACL, Authenticode policy and synthetic native smoke
belong to P1C-G2. Real PPK selection, passphrase entry, DPAPI custody, signing,
publish, promote, Release, Deploy and Production remain unexecuted.

## P1C-G2 packaged helper composition checkpoint

P1C-G2 preserves the canonical `packaging/task036_shell.spec` Main Product
definition and adds a two-stage internal helper build. A console-enabled
one-file helper keeps anonymous stdin/stdout available while the parent
controller still applies `CREATE_NO_WINDOW`.

The Main build computes the staged helper SHA-256, generates a top-level
identity module inside the Main PYZ, and collects the exact same helper bytes
as `BAI Video Production Key Helper.exe` beside the Main EXE. The canonical
runtime factory derives the adjacent path only from frozen `sys.executable`
and reads the digest only from the embedded module; it accepts neither caller
path nor caller digest.

The Windows build and body-free verifier require staging helper, bundled
helper and generated module to agree. Secret-free native smoke proves protocol
v1 empty-input exit 0 and invalid-version exit 64. Actual Windows build uses
Python `3.12.4` / PyInstaller `6.22.0`; helper and Main package build,
three-way identity verification, embedded-module archive inspection and both
native smokes pass.

Focused tests are `34 PASS`; direct P1C/TASK-029 R9B/packaging regression is
`136 PASS`. The correctly rooted Product-wide Windows run produced
`4275 PASS / 5 skip`, one transient native Tk traversal failure and two known
oversized parameter-ID setup errors. The Tk case passed alone; the exact five
oversized functional cases passed under WSL. Detailed Evidence is
`ppk-packaged-helper-composition-p1cg2-evidence.md`.

The next unit is P1C-H native file selection and masked passphrase adapter.
Real PPK/passphrase use, DPAPI custody, signing, Authenticode, installer,
publish, promote, Release, Deploy and Production remain separate Gates.
