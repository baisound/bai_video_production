# TASK-059 P1C-H1 - Native Secret Adapter Contract and Evidence

Date: `2026-08-27`

Status: `IMPLEMENTED_SYNTHETIC_WINDOWS_PASS`

Development depth: `DEV-4 PRIVACY, AUTHORIZATION AND RELEASE INTEGRITY`

## Atomic Unit

P1C-H1 owns the Python-local adapter contract between the future Windows native
file/passphrase dialog and the existing P1C-E one-use Operator Session.

It does not implement the concrete Windows masked dialog, expose a Shell API,
wire the Settings card, read an Owner key, start real DPAPI custody, sign,
publish, promote, release or deploy.

## Design boundary

The adapter implements this exact transient route:

1. require the P1C-G2 adjacent helper identity to be present and digest-valid;
2. select one absolute regular non-symlink `.ppk` and one `.pub` path through
   an injected native backend;
3. read each file with a bounded mutable buffer and perform the existing P0
   public-coordinate preflight;
4. return a body-free candidate containing only opaque ID, public fingerprint,
   algorithms and digests;
5. require an explicit public-identity confirmation;
6. revalidate helper availability before displaying the secret dialog;
7. allocate one caller-owned 1024-byte mutable buffer and require the backend to
   write UTF-8 bytes directly into it;
8. reject empty, NUL-bearing, malformed UTF-8, undeclared-tail or oversized
   output without creating an immutable passphrase copy;
9. re-read both selected files immediately before P1C-E and require exact P0
   payload equality;
10. transfer the same mutable passphrase buffer and fresh mutable file buffers
    to one P1C-E Session;
11. expose only a path-free READY projection and delegate explicit
    confirm/cancel once;
12. clear every mutable buffer on success, cancel and failure.

No path, file body, passphrase, exception detail or custody destination is
included in the candidate/READY dictionaries or repr output.

## Failure behavior

Fixed body-free codes distinguish:

- packaged helper unavailable before selection or secret collection;
- native file/secret dialog unavailable;
- invalid file selection or public preflight;
- stale/missing candidate and active attempt;
- public confirmation missing;
- invalid native secret-buffer output;
- file identity changed after public confirmation;
- downstream P1C-E helper/custody failures.

A helper identity drift before secret entry prevents the passphrase backend from
being called. A selected-file drift after secret entry prevents Session
construction. False final confirmation keeps READY available for explicit
Cancel; replay after success is rejected.

## Verification

Windows Python `3.12.4`:

- P1C-H1 focused: `17 PASS`
- P1C-H1 plus P1C-E direct: `27 PASS`
- all TASK-059 direct suites: `160 PASS / 2 known Pytest 9 oversized
  parameter-ID setup errors`
- exact pure P0 preflight suite under WSL: `26 PASS`
- module/test `py_compile`: `PASS`
- diff whitespace check: `PASS`

The two Windows setup errors occur while Pytest creates paths from intentionally
oversized parameter values and match the already recorded P1C-G2 harness
limitation. They are not test assertion failures. The complete pure P0
preflight suite, including its oversized values, passes under WSL. WSL cannot
collect the secret-bearing suites because its older cryptography package lacks
Argon2id; no dependency installation was performed.

## Critic and Judge

Critic found one High issue in the first implementation: packaged-helper
identity was verified only when P1C-E started, after native file/passphrase
collection. The adapter now probes helper identity before file selection and
again immediately before secret collection. Negative tests prove that neither
backend is invoked after the corresponding failure.

Residual Critical/High/Medium/Low: `0 / 0 / 0 / 0`.

Judge decision: `GO` for the H1 contract and synthetic fixtures.

## Next boundary

P1C-H2 may implement the concrete Windows backend. It must preserve the
caller-owned mutable-buffer contract and must not use Tk `askstring`,
PowerShell stdout, clipboard, argv, environment, temp files, logs, WebView
JavaScript or JSON for the passphrase.

Real PPK/passphrase use, DPAPI custody, signing, Authenticode, installer,
publish, promote, Release, Deploy and Production remain separate Gates.
