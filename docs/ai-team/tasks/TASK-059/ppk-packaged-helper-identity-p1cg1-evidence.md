# TASK-059 P1C-G1 - Packaged Helper Identity Evidence

Date: `2026-08-27`

Status: `LOCAL_IMPLEMENTATION_PASS_PACKAGING_NOT_EXECUTED`

Development depth: `DEV-4 PRIVACY, AUTHORIZATION AND RELEASE INTEGRITY`

## Atomic Unit

P1C-G1 owns only the controller-side identity and admission contract for the
future packaged key helper. It does not own PyInstaller composition, installer
placement, Authenticode, Operator UI, passphrase capture, real custody or
signing.

Changed implementation:

- `owner_signing_key_ppk_process_controller.py`
- `test_task059_owner_signing_key_ppk_process_controller.py`

## Implemented boundary

- Development remains the exact isolated Python-module command:
  `python -I -u -m ai_video_production.owner_signing_key_ppk_helper
  --protocol-version 1`.
- Packaged mode admits only the exact basename
  `BAI Video Production Key Helper.exe` and fixed
  `--protocol-version 1` arguments.
- The executable identity must be absolute and carry a pinned lowercase
  `sha256:<64 lowercase hex>` coordinate.
- Packaged mode is Windows-only and never uses PATH lookup, shell execution,
  stderr capture or caller-supplied arguments.
- The executable must be a non-symlink regular file between 1 byte and 128 MiB.
- SHA-256 is read from one open handle. Device, inode, size and modification
  coordinates must remain stable across the read.
- The verified handle remains open through the process-creation call. Identity
  failure consumes the one-use controller before any subprocess call.
- Every identity rejection maps to the fixed body-free
  `ERR_PPK_HELPER_IDENTITY_MISMATCH` code.

## Failure-mode review

The first implementation verified a path and then closed it before calling the
process factory. Critic identified a substitution interval between digest
verification and process creation. The implementation was corrected to retain
the verified file handle across the process-creation call.

This reduces path substitution exposure but does not claim that Windows creates
the process from that Python handle. The subprocess API still launches by path.
Signed-package origin, exact adjacent placement, installation ACL, trusted
digest provenance and native Windows observation remain P1C-G2 requirements.
P1C-G1 therefore does not claim Authenticode, installed-image integrity or
runtime proof.

## Verification

Executed on Windows Python 3.12:

- source and focused-test `py_compile`: `PASS`
- focused process-controller suite: `21 PASS`
- direct TASK-059 P1C-E/P1C-D/P1C-B/wire/P1B/P1A plus TASK-029 R9B:
  `123 PASS`

Covered positive and negative boundaries include:

- unchanged development argv;
- valid pinned packaged identity and exact packaged argv;
- wrong basename, absent digest and malformed digest rejection;
- tampered content and digest mismatch rejection before subprocess creation;
- non-Windows packaged-mode rejection;
- empty, oversized and non-regular identity rejection;
- one-use consumption after identity failure; and
- preserved no-shell, no-console, DEVNULL stderr and environment allowlist.

Not executed:

- PyInstaller or equivalent packaged-helper build;
- creation or installation of a real helper executable;
- Authenticode signing or validation;
- native packaged-helper subprocess smoke;
- real PPK, passphrase, private-key, seed, DPAPI custody or signing; and
- publish, promotion, Release, Deploy or Production.

No secret value or real key material was read, written, logged, transmitted or
persisted by this Atomic Unit.

## Critic / Judge

Resolved High finding: path verification previously ended before process
creation. The verified handle is now held through the process factory call,
while the remaining OS/package trust boundary is explicitly assigned to
P1C-G2.

Residual findings within P1C-G1 scope:
`Critical / High / Medium / Low = 0 / 0 / 0 / 0`.

Decision: `GO` for commit-ready P1C-G1 only.

Next: P1C-G2 packaging composition, trusted digest generation, adjacent
placement policy and synthetic native smoke. No real-key Gate is opened.
