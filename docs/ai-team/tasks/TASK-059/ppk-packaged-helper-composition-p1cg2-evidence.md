# TASK-059 P1C-G2 - Packaged Helper Composition Evidence

Date: `2026-08-27`

Status: `LOCAL_WINDOWS_BUILD_AND_NATIVE_SMOKE_PASS`

Development depth: `DEV-4 PRIVACY, AUTHORIZATION AND RELEASE INTEGRITY`

## Atomic Unit

P1C-G2 owns packaging composition, embedded digest provenance, exact adjacent
placement, build-time read-back and secret-free native helper smoke. It does
not own Operator file selection, passphrase capture, real custody, signing,
Authenticode, installer publication or Release.

## Design and implementation

The canonical Main Product continues to use
`packaging/task036_shell.spec`. The two-stage build is:

1. Build `BAI Video Production Key Helper.exe` as an internal console-enabled
   one-file executable. Console mode preserves binary stdin/stdout; the P1C-B
   parent still launches it with `CREATE_NO_WINDOW`.
2. Main spec receives the exact staged helper path through the build-process
   scoped `BVP_TASK059_HELPER_EXE` variable.
3. Main spec validates filename, regular-file/symlink/size bounds, hashes the
   helper and writes only its SHA-256 coordinate to
   `_bvp_task059_packaged_helper_identity.py`.
4. That module is included in the Main PYZ and the same helper is collected as
   an `EXECUTABLE` at the one-dir root beside
   `BAI Video Production.exe`.
5. The runtime factory accepts no arguments. It requires frozen execution,
   derives the adjacent path from `sys.executable` and loads only the digest
   embedded in the Main archive.
6. A body-free build verifier compares the staging helper, bundled helper and
   generated module before native smoke.

No mutable adjacent manifest is used as the runtime trust anchor. Modifying
only the helper after build causes controller SHA-256 admission failure.
Replacing both Main and helper remains outside this unsigned local-build
boundary and requires the separate Authenticode/installer Gate.

## Changed paths

- `packaging/task059_ppk_helper_windows_entry.py`
- `packaging/task059_ppk_helper.spec`
- `packaging/task036_shell.spec`
- `build-windows-exe.bat`
- `tools/windows/verify-task059-packaged-helper.py`
- `src/ai_video_production/owner_signing_key_ppk_process_controller.py`
- `tests/test_task059_packaged_helper_build.py`
- `tests/test_task059_owner_signing_key_ppk_process_controller.py`
- `docs/windows/BUILDING-WINDOWS-EXE.md`
- `docs/ai-team/tasks/TASK-059/p1cg2-windows-build-operation-procedure-2026-08-27.md`
- this Evidence and bounded TASK-059 status synchronization

## Windows build and native observations

Environment:

- Windows 11 `10.0.26200`
- Python `3.12.4`
- PyInstaller `6.22.0`
- PyInstaller contrib hooks `2026.6`

Observed output:

- Main EXE size: `16,324,300`
- Main EXE:
  `sha256:9cc7cae6d18b8cdab5e1e972231d4c84d820968fd1d066b4a5d800f457d23e89`
- staged helper size: `17,229,081`
- bundled helper size: `17,229,081`
- staged and bundled helper:
  `sha256:296967c0a674eacddc7cc95a06de163d233d2f2a86d95d48281076218d068caa`
- generated identity module contains the same helper SHA-256 coordinate
- recursive PyInstaller archive inspection finds
  `_bvp_task059_packaged_helper_identity` inside the Main EXE

Native smoke:

- protocol v1 with empty stdin: `PASS / exit 0`
- invalid protocol version: `PASS / exit 64`
- staging/bundle/generated identity verifier: `PASS`

The Main UI was not launched. The helper received no AUTH_REQUEST and no key or
passphrase.

## Verification

Final focused Windows run:

- compile controller, verifier and their tests: `PASS`
- controller/trust anchor + verifier/spec/batch + existing TASK-036/TASK-042
  packaging contract: `34 PASS`

Final direct Windows regression:

- P1C-G2/G1/P1C-E/P1C-D/P1C-B/wire/P1B/P1A;
- TASK-029 R9B custody; and
- TASK-036/TASK-042 packaging;
- result: `136 PASS`

Product-wide diagnostic:

- an initial invocation used the Primary checkout as cwd, so relative schema
  reads pointed at the wrong checkout. Its failures are invalid as Product
  evidence and were not treated as code failures.
- correct external-worktree cwd: `4275 PASS / 5 skip / 1 fail / 2 setup
  errors`.
- the one failure was TASK-054 native Tk traversal and passed immediately when
  rerun alone: `1 PASS`. It is a non-reproducible GUI timing observation.
- the two setup errors occurred before test execution because Windows/Pytest 9
  attempted to use oversized parameter values as temporary path identifiers.
  The exact functional parameterized test passed under WSL: `5 PASS`.

The monolithic Windows invocation is recorded as `FAIL`, not relabeled PASS.
Required P1C-G2 focused/direct/build/native gates are independently `PASS`,
and every non-product failure was reproduced at its boundary with passing
functional evidence.

## Critic findings and fixes

1. `HIGH / CLOSED`: the first COLLECT entry used `BINARY`, which PyInstaller
   6.22 places under `_internal`. The build correctly failed its adjacency
   Gate. Local PyInstaller source confirmed that `EXECUTABLE` is placed at the
   one-dir root; the TOC type and test were corrected and the full build passed.
2. `HIGH / CLOSED`: digest verification alone did not prove the identity
   module was actually embedded. Recursive archive inspection now supplies
   direct observation of the generated module inside the Main EXE.
3. `HIGH / CLOSED`: the build verifier originally body-freed only expected
   `ValueError`. Unexpected filesystem/race exceptions could expose paths.
   The CLI boundary now converts every exception to one fixed error and tests
   unexpected-exception redaction.
4. `MEDIUM / CLOSED`: canonical spec direct invocations now require helper
   prebuild state. Current non-historical code search shows the root batch is
   the sole build invoker; the documented canonical route remains the batch.
5. `MEDIUM / CLOSED`: build success could be mistaken for signed-release
   integrity. Documentation and UI boundary state that local EXEs are unsigned
   and do not prove Authenticode, installer or Release readiness.

Residual findings:
`Critical / High / Medium / Low = 0 / 0 / 0 / 0`.

## Authority and effects

Owner-authorized PC operation was used for the local Windows build and
secret-free helper smoke. Required procedure
`TASK-059-P1CG2-WINDOWS-BUILD-OPERATION-PROCEDURE-20260827` was created at
`docs/ai-team/tasks/TASK-059/p1cg2-windows-build-operation-procedure-2026-08-27.md`
and sent unchanged to the BAI DEVELOPMENT OS `秘書` task.

- install: `NOT_EXECUTED`
- download: `NOT_EXECUTED`
- settings change: `NOT_EXECUTED`
- Main UI / Project / Resolve / Cubase operation: `NOT_EXECUTED`
- real PPK/public key/passphrase/seed/private key: `NOT_READ`
- DPAPI custody/signing/publish/promote/Release/Deploy/Production:
  `NOT_EXECUTED`
- generated build outputs: ignored local `builds/**` only
- rollback: `NOT_REQUIRED / NOT_EXECUTED`

Decision: `GO` for commit-ready P1C-G2.

Next: P1C-H native file selection and masked passphrase adapter using synthetic
fixtures only. Real-key use remains a separate Human Gate.
