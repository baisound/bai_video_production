# TASK-059 P1C-I - Body-free Shell API and Connection / Secret UI Evidence

Date: `2026-08-27`

Identity: `TASK-059-P1CI-SHELL-API-UI-EVIDENCE-V1`

Status: `PASS_NATIVE_MANUAL_QA_NEXT`

Development depth: `DEV-4 PRIVACY, AUTHORIZATION AND RELEASE INTEGRITY`

## Outcome

The canonical unified `BAI Video Production.exe` Settings route now contains
one additive `Owner signing key` card under `Connection / Secret`. No second
Product, window, custody store or signing path was introduced.

The Shell API is body-free. WebView receives only an opaque candidate/attempt
identifier, public OpenSSH SHA-256 fingerprint, algorithm facts, fixed states,
fixed Japanese error text and receipt digests. Selected paths, file bodies,
passphrase bytes, Owner scope and the custody destination path remain inside
Python/native code.

## Implemented contract

- Added `OwnerSigningKeyPpkShellService` as the single transient coordinator
  over the existing H1 adapter and P1C-E session.
- Added a public helper-availability probe which performs no file or secret
  dialog operation and fails with one fixed body-free code.
- Added six allowlisted Shell methods:
  - `owner_signing_key_import_snapshot`
  - `owner_signing_key_import_choose_files`
  - `owner_signing_key_import_confirm_public_identity`
  - `owner_signing_key_import_open_native_secret_dialog`
  - `owner_signing_key_import_confirm_ready`
  - `owner_signing_key_import_cancel`
- Shell request shapes reject paths, bodies, passphrases, retries and false
  confirmation values.
- The card exposes the five-step Operator route: select files, inspect and
  explicitly confirm the public identity, open the native masked dialog,
  explicitly confirm one-shot import, then show read-back-verified receipt
  coordinates.
- Closing Settings or pressing Escape cancels the active candidate/attempt.
- Final import has no default Enter behavior. It requires click or Space and a
  second explicit confirmation.
- `ERR_PPK_CUSTODY_RESULT_LOST_REQUIRES_READBACK` enters
  `READBACK_REQUIRED_NO_RETRY`; new selection is never dispatched. Only the
  existing custody read-back provider may resolve it.
- Success offers no automatic signing action and declares signing, publication,
  promotion, Release and Deploy as not authorized/not started.

## Critic and fix

High finding: accepting an arbitrary destination display label could allow a
caller to accidentally expose the real custody path through WebView.

Fix: removed the constructor-supplied display label. The card now uses one
fixed safe label, while the actual destination path remains internal.

High finding: Settings close and Escape cancelled transient state, but a
WebView refresh had no explicit cancellation hook.

Fix: `beforeunload` now sends only the opaque current coordinate to the
allowlisted Cancel method. Parent death remains the independent helper-side
fail-safe.

Residual Critical/High/Medium/Low: `0 / 0 / 0 / 0`.

## Verification

Executed on Windows Python 3.12:

- P1C-I + H1/H2/native-dialog focused and negative regression:
  `58 PASS`.
- Existing TASK-036 Shell Settings plus direct TASK-059/native-dialog
  regression with the five known oversized-parameter test cases excluded:
  `235 PASS / 5 DESELECTED`.
- The unchanged Windows Pytest 9 parameter-ID filesystem limitation remains
  outside Product behavior; no new functional failure was observed.
- Extracted canonical Settings JavaScript parsed with Node `--check`: `PASS`.
- `git diff --check`: `PASS`.
- Static secret/path audit: no real key path, key identity, key body, private
  seed or passphrase transport was added.

## Runtime boundary

The production bridge accepts an optional trusted service binding. When exact
expected fingerprint, Owner-scope digest or canonical custody destination
configuration is absent, the card is visible but fail-closed as
`UNAVAILABLE_CONFIGURATION`.

Actual Credential UI, real PPK/passphrase, real DPAPI custody, Authenticode,
installer, signing, publish, promote, Release, Deploy and Production were not
executed. Masking, focus, accessibility, Cancel/OK and timeout observation
remain P1C-J manual native QA / separate real-key Human Gate.
