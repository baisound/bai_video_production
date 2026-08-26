# TASK-059 P1C-E - Parent Operator Session Evidence

Date: `2026-08-27`

Status: `LOCAL_IMPLEMENTATION_PASS_TK_OPERATOR_UI_NEXT`

Development depth: `DEV-4 PRIVACY, AUTHORIZATION AND RELEASE INTEGRITY`

## Responsibility boundary

P1C-E adds one transient parent-side Session over the existing P1C-B process
controller. It starts one fixed helper, drives the exact P1C state machine and
returns only the P1B body-free result. It does not implement cryptography,
custody, signing, persistence or a GUI toolkit.

The Session owns transferred mutable PPK, RFC4716 public-key and passphrase
buffers. All three are zeroed after the AUTH_REQUEST write attempt and on every
pre-send validation failure. The destination encoding buffer is also zeroed.
The secret-bearing frame is not retained by the Session.

## Operator flow

The only READY projection contains the fingerprint, transient destination
display, expiry and fixed Japanese labels for the one-shot consequence,
explicit import action and Cancel. Its repr redacts the destination path. The
Session itself does not retain destination plaintext after READY.

Confirmation accepts only literal `True` and is compiled from the exact READY
record at click time. False confirmation sends nothing and keeps Cancel
available. Cancel emits the sole fixed Owner cancellation frame. Every Session
is one-use, including failed starts.

The parent independently re-admits P0 and cross-binds READY to the exact
preflight hash, PPK hash, signer ID, fingerprint, Owner scope and canonical
destination hash. A canonical but crossed READY is rejected and the helper is
aborted.

## Failure and recovery

Helper body-free failure codes are preserved without exception text. In
particular, `ERR_PPK_CUSTODY_RESULT_LOST_REQUIRES_READBACK` remains terminal;
the parent never starts a second attempt or silently retries custody.
Controller, wire and Product errors are reduced to fixed code-only
`PpkImportOperatorError` values.

## Verification

- Windows Python 3.12 compile: `PASS`
- P1C-E focused tests: `10 PASS`
- P1C-E plus P1C-D/P1C-B/P1C/P1B/P1A/R9B direct regression: `117 PASS`
- success, Cancel, false-confirmation, one-use, start/send failure and close:
  `PASS`
- transferred-buffer zeroing on valid and invalid input: `PASS`
- canonical READY cross-binding drift: `PASS`
- authentication failure and custody-result-lost code preservation: `PASS`

No real helper subprocess, real PPK/passphrase, DPAPI custody, signing, file
dialog, Tk window, installation, release, deploy or Production action was
executed. The next bounded unit is Tk Operator wiring over this Session with
synthetic controller fixtures.

## Critic / Judge

Critic found and corrected two parent-boundary gaps:

1. malformed companion input could leave another transferred mutable buffer
   uncleared; and
2. READY needed a parent-side cross-binding check rather than relying only on
   helper construction.

The final Session retains no secret-bearing frame and no destination plaintext,
has no retry path and creates no new custody owner or execution authority.

Residual Critical/High/Medium/Low: `0 / 0 / 0 / 0`.

Decision: `GO` for synthetic-only Tk Operator wiring. Real key import, DPAPI
custody and signing remain separate Human Gates.
