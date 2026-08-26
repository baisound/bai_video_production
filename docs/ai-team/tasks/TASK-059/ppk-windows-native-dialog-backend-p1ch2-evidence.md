# TASK-059 P1C-H2 - Windows Native Dialog Backend Evidence

Date: `2026-08-27`

Status: `IMPLEMENTED_SYNTHETIC_AND_NATIVE_SYMBOL_PASS_GUI_QA_NOT_CONFIRMED`

Development depth: `DEV-4 PRIVACY, AUTHORIZATION AND RELEASE INTEGRITY`

## Implementation

P1C-H2 provides the concrete Windows implementation of the P1C-H1 backend.

- Existing `WindowsNativeFileDialog` gains two fixed, single-selection
  WinForms filters: encrypted `.ppk` and RFC4716 `.pub`.
- The passphrase uses `CredUIPromptForCredentialsW`, not PowerShell, Tk,
  WebView, JSON, argv, environment, temp files, logs or Product clipboard APIs.
- Fixed flags are `GENERIC_CREDENTIALS | ALWAYS_SHOW_UI | DO_NOT_PERSIST |
  EXCLUDE_CERTIFICATES | KEEP_USERNAME` (`0x14008a`).
- Username is a fixed non-secret label and cannot be changed.
- Windows writes the password into a caller-provided UTF-16 buffer.
- Numeric UTF-16 code units are converted directly into H1's caller-owned
  UTF-8 `bytearray`; the production path never materializes the passphrase as
  a Python `str` or immutable `bytes`.
- NUL, invalid/truncated surrogate, byte-ceiling overflow, malformed count and
  undeclared native-buffer tail fail closed.
- The Windows buffer is cleared with `RtlSecureZeroMemory`; a ctypes FFI
  memset fallback exists only if that entrypoint cannot be loaded.
- Cancel returns no secret, and every error remains a fixed body-free code.

The flag and buffer behavior was checked against Microsoft's
`CredUIPromptForCredentialsW` documentation:
https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-creduipromptforcredentialsw

## Verification

Windows Python `3.12.4`:

- H2 core: `14 PASS`
- H2 + fixed file chooser + H1: `42 PASS`
- TASK-059 + native dialog direct regression:
  `185 PASS / 2 known Pytest 9 oversized parameter-ID setup errors`
- pure P0 preflight under WSL: `26 PASS`
- compile/static/diff checks: `PASS`

Read-only Windows native probe:

- `credui.dll` load: `PASS`
- `CredUIPromptForCredentialsW`: present
- `CREDUI_INFOW` size: `40`
- exact flags: `0x14008a`

The two Windows setup errors are the unchanged P1C-G2 oversized parameter-ID
harness limitation, not assertion failures.

## Critic and Judge

High finding: the first H1 implementation collected file/secret inputs before
an explicit packaged-helper preflight. Resolved in H1 by checking the helper
before each native boundary.

High finding: Microsoft requires password memory clearing after use. The H2
native buffer now uses the documented `RtlSecureZeroMemory` boundary, with
tests retaining the ctypes buffer and proving it is zero after success, Cancel
and failure.

The Product invokes no clipboard API and never writes a passphrase to the
clipboard. Operator-initiated OS input behavior is not used as a Product data
transport and was not automated.

Residual Critical/High/Medium/Low: `0 / 0 / 0 / 0` for implementation and
synthetic/native-symbol Evidence.

Judge decision: `GO` for P1C-H2 implementation. Actual Credential UI visual,
masking, focus, accessibility, Cancel and OK observation remain
`NOT_CONFIRMED`, because the applicable Computer Use safety policy prohibits
automation of authentication dialogs. That observation belongs to the P1C-J
manual native Human Gate and is not claimed PASS here.

## Effects

No real PPK/public key/passphrase was read. No DPAPI custody, signing,
publication, promotion, install, download, settings mutation, Release, Deploy
or Production effect occurred. Rollback is `NOT_REQUIRED`.
