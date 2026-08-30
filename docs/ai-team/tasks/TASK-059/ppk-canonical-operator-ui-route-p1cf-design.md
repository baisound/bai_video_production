# TASK-059 P1C-F - Canonical Operator UI Route Design

Date: `2026-08-27`

Status: `DESIGN_BOUND_PACKAGED_HELPER_IDENTITY_NEXT`

Development depth: `DEV-4 PRIVACY, AUTHORIZATION AND RELEASE INTEGRITY`

## Canonical entrypoint decision

The PPK import flow belongs in the unified `BAI Video Production.exe` Settings
overlay under `Connection / Secret`, in one `Owner signing key` card. A
standalone Tk product, a second Settings window and a second custody utility are
rejected.

A native local dialog may be opened by the unified Shell for file selection and
masked passphrase entry, but it remains an adapter owned by the same Product
flow. It is not another Product entrypoint and must return only to the P1C-E
Session.

## Operator journey

The card uses a short five-step route:

1. `Status`: show `NOT CONFIGURED`, `READY TO IMPORT`, `CUSTODIED` or a
   fixed recovery state. Never show a secret, key body or custody file body.
2. `Select files`: one explicit click opens native selectors for the encrypted
   PPK and RFC4716 public key. Selected paths and file bodies remain Python-local
   and are not returned through WebView JSON.
3. `Confirm public identity`: show the OpenSSH SHA-256 fingerprint, PPK v3 /
   Ed25519 / Argon2id facts and the one-shot/no-overwrite consequence. Continue
   requires a direct click; no default Enter action.
4. `Enter passphrase`: open a native masked dialog. The value is created as a
   bounded mutable UTF-8 buffer and passed directly to P1C-E. It never crosses
   JavaScript, WebView RPC, argv, environment, clipboard, temp, logs or Evidence.
5. `READY confirmation`: show fingerprint, destination display, expiry and the
   exact one-shot consequence from the P1C-E projection. Only the explicit
   `Confirm and import` click sends CONFIRM. Escape and window close are Cancel.

The card always displays `This does not sign, publish, promote, release or
deploy`. Success shows only signer ID, receipt digests and read-back verified
state. It does not offer an automatic next signing action.

## API and secret boundary

WebView-visible methods are body-free:

- `owner_signing_key_import_snapshot()`
- `owner_signing_key_import_choose_files()`
- `owner_signing_key_import_confirm_public_identity(candidate_id, true)`
- `owner_signing_key_import_open_native_secret_dialog(candidate_id)`
- `owner_signing_key_import_confirm_ready(attempt_id, true)`
- `owner_signing_key_import_cancel(attempt_id)`

The choose-files call may return only an opaque candidate ID, public
fingerprint, algorithms, body-free hashes and safe state. It returns no path or
file body. Python re-reads both files immediately before P1C-E begin and requires
their exact P0 hashes to match, closing the file-selection TOCTOU boundary.

The native secret dialog invokes P1C-E in-process and returns only READY or a
fixed code to the Shell. The passphrase is never an API argument or result.
Generic Shell request logging must receive no secret-bearing method payload.

## Interaction and accessibility

- Settings opens directly to the existing `Connection / Secret` tab; the
  signing-key card is after Provider credentials, not hidden under Advanced.
- Each state shows one recommended primary action and one Cancel/Close action.
- Buttons carry exact disabled reasons. Import is disabled before READY.
- Fingerprint uses a selectable monospace display; key body is never displayed.
- Focus moves to the state heading after each transition.
- Screen-reader labels state `one-shot import` and `no overwrite`.
- Enter never confirms import; Escape cancels the current attempt.
- Error text is a Japanese mapping from fixed codes only. Exception text,
  absolute paths and provider/library details are not rendered.
- `RESULT LOST - READ BACK REQUIRED` disables retry and presents only the
  canonical read-back recovery action.

## Packaged helper dependency

P1C-B currently has only the development Python-module command:

`python -I -u -m ai_video_production.owner_signing_key_ppk_helper ...`

The unified frozen Product cannot treat its own EXE as that Python interpreter.
Before the UI action is enabled, P1C-G must add one exact packaged-helper launch
identity, expected adjacent filename/digest and a controller command that does
not accept arbitrary argv. The existing development command and the packaged
command must be distinct exact variants; neither may fall back to PATH search.

The helper remains an internal short-lived process. The user launches only the
unified Product. Missing, moved, unsigned or digest-mismatched helper identity
keeps the card disabled before file selection or passphrase entry.

## State and recovery

```text
UNAVAILABLE_PACKAGED_HELPER
  -> IDLE_NOT_CONFIGURED
  -> FILES_SELECTED_PUBLIC_CANDIDATE
  -> PUBLIC_IDENTITY_CONFIRMED
  -> NATIVE_SECRET_DIALOG_ACTIVE
  -> READY_FOR_EXPLICIT_IMPORT
  -> CUSTODIED_READBACK_VERIFIED
```

Cancel before READY clears candidate state and starts no custody. Cancel after
READY terminates the helper. Authentication failure returns to IDLE only after
process termination. Custody result loss enters
`READBACK_REQUIRED_NO_RETRY`; no new attempt can begin until canonical R9B
read-back resolves whether custody exists.

Browser refresh, Shell close and parent death cancel the active helper and do
not retain passphrase or AUTH_REQUEST. Only body-free candidate/session
coordinates may be transiently held; no new persistent store is introduced.

## Atomic implementation order

1. P1C-G: exact packaged helper identity, controller variant and packaging
   composition with synthetic native smoke.
2. P1C-H: native file selection and masked passphrase adapter with no WebView
   secret transport.
3. P1C-I: body-free Shell API and `Connection / Secret` card wiring.
4. P1C-J: packaged Windows accessibility, focus, Cancel, timeout and
   result-lost recovery QA.
5. Separate real-key Human Gate: real PPK/passphrase and R9B DPAPI custody.

## Critic / Judge

Critical finding: implementing the previously named Tk panel would create a
second Product route and still leave the packaged helper unlaunchable.
Resolved by binding the flow to the unified Settings card and ordering packaged
helper identity before UI enablement.

Critical finding: a normal WebView form/RPC would copy the passphrase into
JavaScript and JSON. Resolved by a native Python-local masked dialog whose value
never becomes a WebView method argument or result.

High finding: file paths or selected bodies could leak through Shell snapshots.
Resolved by opaque candidate IDs, body-free coordinates and Python-local
re-read/hash comparison.

High finding: an ambiguous custody result could invite a retry button. Resolved
by a dedicated read-back-required terminal UI state with retry disabled.

Residual Critical/High/Medium/Low: `0 / 0 / 0 / 0` for this design.

Decision: `GO` for P1C-G packaged helper identity only. UI enablement, real
file selection, passphrase entry, DPAPI custody and signing remain unexecuted.
