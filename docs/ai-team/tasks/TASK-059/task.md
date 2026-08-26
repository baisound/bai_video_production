# TASK-059 — Owner Signing Key PPK Import Bridge

Status: `P1CJ4_CURRENT_BUILD_PASS_GUI_NOT_CONFIRMED`

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

## P1C-H1 native secret adapter contract checkpoint

P1C-H1 adds the Python-local transient adapter over P0, P1C-E and the P1C-G2
packaged-helper identity. It validates the helper before file selection and
again before secret collection, retains selected paths only inside Python,
returns path/body-free candidate and READY projections, requires explicit
public-identity confirmation, and re-reads both files with exact P0 equality
immediately before Session begin.

The secret backend can write only into one caller-owned bounded mutable buffer.
H1 validates UTF-8 without a string/immutable-secret conversion and clears that
buffer plus both file buffers on every success, cancel and failure path. Helper
or selected-file drift fails before Session dispatch. Final Confirm/Cancel
remain one-use P1C-E operations.

P1C-H1 focused Evidence is `17 PASS`; P1C-H1 plus P1C-E is `27 PASS`.
All TASK-059 direct Windows suites are `160 PASS` plus the two already-known
Pytest 9 oversized parameter-ID setup errors; the complete pure P0 suite is
`26 PASS` under WSL. Critic found and resolved the helper-preflight timing
gap; residual Critical/High/Medium/Low is `0 / 0 / 0 / 0`. Detailed Evidence
is `ppk-native-secret-adapter-contract-p1ch1-evidence.md`.

P1C-H2 next owns the concrete Windows masked secret dialog and fixed PPK/public
file filters. Real PPK/passphrase use, DPAPI custody, signing, Authenticode,
installer, publish, promote, Release, Deploy and Production remain separate
Gates.

## P1C-H2 Windows native dialog backend checkpoint

P1C-H2 adds fixed encrypted-PPK/RFC4716 WinForms file selectors and the
concrete Windows Credential UI secret backend. `DO_NOT_PERSIST`,
`GENERIC_CREDENTIALS`, `ALWAYS_SHOW_UI`, certificate exclusion and a locked
non-secret username are fixed. Windows writes into caller-owned UTF-16 memory;
numeric conversion writes directly into H1's UTF-8 `bytearray`, and
`RtlSecureZeroMemory` clears native memory on every path.

H2 core Evidence is `14 PASS`; H2/file-dialog/H1 focused Evidence is
`42 PASS`; TASK-059 plus native-dialog direct Windows regression is
`185 PASS` plus the two known Pytest 9 oversized parameter-ID setup errors.
The read-only native probe confirms `credui.dll`,
`CredUIPromptForCredentialsW`, 40-byte `CREDUI_INFOW` and exact
`0x14008a` flags.

Actual Credential UI automation was not executed because the applicable
Computer Use safety policy prohibits automating authentication dialogs.
Masking/focus/accessibility/Cancel/OK runtime observation remains
`NOT_CONFIRMED` for P1C-J manual native QA. Detailed Evidence is
`ppk-windows-native-dialog-backend-p1ch2-evidence.md`.

P1C-I next owns body-free Shell API and the canonical Settings
`Connection / Secret` card. Real PPK/passphrase use, DPAPI custody, signing,
Authenticode, installer, publish, promote, Release, Deploy and Production
remain separate Gates.

## P1C-I body-free Shell API and Settings card checkpoint

P1C-I connects the existing H1/H2 native adapter to the unified TASK-036 Shell
through six exact body-free methods and adds one `Owner signing key` card after
Provider credentials in Settings `Connection / Secret`. The Operator receives
only opaque candidate/attempt IDs, public identity facts, fixed status/error
text and receipt digests. File paths, bodies, passphrase, Owner scope and the
custody destination path remain Python/native-local.

The card provides explicit public-identity confirmation, native masked secret
entry, a no-default-Enter one-shot import confirmation, cancel-on-Settings-close
and a retry-disabled `READBACK_REQUIRED_NO_RETRY` route. Success creates no
automatic signing action and does not authorize publish, promote, Release,
Deploy or Production.

P1C-I/H1/H2 focused Evidence is `58 PASS`; existing TASK-036 Shell plus direct
TASK-059/native-dialog regression is `235 PASS / 5 DESELECTED` for the known
Windows Pytest oversized-parameter-ID cases. Canonical Settings JavaScript
syntax, diff and secret/path audits pass. Critic found and fixed an arbitrary
destination-display leak risk by making the UI label constant, and closed the
WebView-refresh transient-cancellation gap with an opaque-ID-only unload hook. Residual
Critical/High/Medium/Low is `0 / 0 / 0 / 0`. Detailed Evidence is
`ppk-shell-api-settings-card-p1ci-evidence.md`.

The real configuration coordinates are not inferred or hardcoded. An unbound
Product runtime shows `UNAVAILABLE_CONFIGURATION`. P1C-J next owns manual
native Windows focus/accessibility/Cancel/OK/timeout/result-lost QA and exact
trusted runtime binding. Real PPK/passphrase, DPAPI custody, signing,
Authenticode, installer, publish, promote, Release, Deploy and Production
remain separate Gates.

## P1C-J1 trusted launcher lifetime binding checkpoint

P1C-J1 adds one optional trusted `OwnerSigningKeyPpkShellService` dependency
to `build_trusted_launch`, passes that exact instance to the canonical
TASK-036 Shell bridge and makes `Task036TrustedLaunch` own its transient
lifetime. Normal close is idempotent. If the signing-key service close fails,
the launch still closes its local-operation lifetime, runtime lease and Product
store before re-raising the service error. Existing in-flight lease close
failure semantics remain retryable and preserve the lease field until close
succeeds.

No expected fingerprint, Owner-scope digest, custody destination, key path or
helper digest is inferred, hardcoded or loaded from an untrusted UI request.
This unit therefore establishes the trusted composition seam without enabling
an unconfigured or real-key import.

P1C-J1 focused lifetime/parallel-close Evidence is `3 PASS`; the full trusted
launcher module is `39 PASS`; launcher plus direct P1C-I Shell bridge/service
regression is `53 PASS`. Residual Critical/High/Medium/Low is
`0 / 0 / 0 / 0`. Detailed Evidence is
`ppk-trusted-launcher-lifetime-binding-p1cj1-evidence.md`.

Actual Credential UI observation remains `NOT_CONFIRMED`. The applicable
Computer Use policy prohibits authentication-dialog automation, and the
available GUI-control kernel did not initialize. Manual native
focus/accessibility/Cancel/OK/timeout/result-lost QA, real PPK/passphrase,
DPAPI custody, signing, Authenticode, installer, publish, promote, Release,
Deploy and Production remain separate Human Gates.

## P1C-J2 trusted runtime configuration checkpoint

P1C-J2 adds strict launch configuration version `1.3.0`. It binds exactly one
public OpenSSH SHA-256 fingerprint, one Owner-scope SHA-256 coordinate and one
absolute custody destination inside the existing private TASK-036 launch
configuration boundary. Legacy versions `1.0.0` through `1.2.0` remain
unbound and backward compatible.

The canonical launcher constructs the existing Windows native dialog adapter,
packaged-helper session and TASK-029 R9B receipt read-back service from those
trusted non-secret coordinates. No WebView method, environment variable, CLI
argument or alternate settings store accepts the coordinates. The nested
configuration has a redacted repr so custody destination and Owner scope cannot
appear through normal launcher representation.

The Shell service now rejects an existing file, directory or broken symlink at
the custody destination before opening the native secret dialog. The helper
still performs its independent exact destination check, closing the race before
custody mutation.

Focused P1C-J2 configuration/factory/destination Evidence is `5 PASS`.
Trusted launcher plus direct P1C-I bridge/service is `57 PASS`. TASK-036
Shell/launcher plus all direct TASK-059 Windows regression is
`273 PASS / 5 DESELECTED`; the five known oversized-parameter cases are
`5 PASS` under WSL. Residual Critical/High/Medium/Low is
`0 / 0 / 0 / 0`. Design and Evidence are
`ppk-trusted-runtime-configuration-p1cj2-design-critic-judge.md` and
`ppk-trusted-runtime-configuration-p1cj2-evidence.md`.

No real `1.3.0` launch configuration was written and no real-key operation was
executed. Exact Owner values, actual Credential UI observation and real DPAPI
custody remain Human Gates.

## P1C-J3 current Windows package build checkpoint

P1C-J3 builds exact commit
`fd539054fa70706eece166d59358b2a1e9cfef78` through the canonical
`build-windows-exe.bat` using the existing Windows Python `3.12.4` and
PyInstaller `6.22.0`. The helper one-file build, Main one-directory build,
three-way packaged-helper identity verification and recursive Main archive
inspection all pass.

The Main EXE is `16426395` bytes with SHA-256
`b6d4936959e48b0e52931dd823ce64732147181c35413c8cc106f17268bd5d39`.
The bundled and staging helpers are exact matches at `17229174` bytes with
SHA-256
`5aefebf7a53806a7d8555206d1f805c3dae1f14c8f36521edc58b6b63a574ca0`.
Secret-free helper protocol v1 empty-input smoke exits `0`; invalid-version
refusal exits `64`.

The Main Product UI and Credential UI were not launched. No real Owner
configuration, PPK, public key, passphrase, DPAPI custody, signing, installer,
publication, promotion, Release, Deploy or Production operation was performed.
Detailed Evidence is `ppk-current-windows-package-build-p1cj3-evidence.md`.
Native manual UI QA and real Owner-value configuration remain separate Human
Gates.

## P1C-J4 current Windows Product launch checkpoint

P1C-J4 rebuilt exact commit
`0813c057eb7214e8308e9d156da9252c258ad964` after the Hosted
cross-platform and Windows fixture-ID repairs. The canonical Main and helper
build, packaged-helper identity check and secret-free helper native smoke pass.
The Main EXE is `16426435` bytes with SHA-256
`8f0cb24dcee4d85342a87d060c338834480d36fec9eeca02fc0838613b8d6a67`;
the staging and bundled helpers are exact matches at `17229588` bytes with
SHA-256
`b9b8b79353697b785fcc048dc0474773a224327a031d88dee4fd08d91cf4180c`.

Computer Use failed before app discovery with a missing kernel-assets path and
failed identically after the required session reset and one recovery attempt.
The Product was not launched, no fallback UI automation was used, and startup
remains `NOT_CONFIRMED`. Detailed Evidence is
`ppk-current-windows-product-launch-p1cj4-evidence.md`.
