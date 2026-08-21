# BAI VIDEO PRODUCTION Windows Python environment installation

Date: 2026-08-21
Owner state: `OWNER_SLEEPING=YES / SLEEP_WINDOW_ACTIVE=YES`
Purpose: create an isolated Windows Python environment for Product-native
Provider and native-shell verification. This procedure does not alter the
ComfyUI embedded Python, system Python, WSL environment or another project.

## Authorized boundary

- Base interpreter:
  `C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`
- Isolated environment:
  `E:\BAI_AI\envs\bvp-native-0.22.0`
- Product source:
  `C:\home\baisound\projects\bai-video-production`
- Product version: `0.22.0`
- Source commit used for this installation: `2aa53dfc4a516f5b9a1eb9cfffbbf41be7222580`
- Phase 1 installs only the Product and its declared mandatory dependency
  `jsonschema>=4.20,<5`.
- Phase 2 may install only the Product-declared native Shell dependency
  `pywebview==6.2.1`. It does not install the remaining `windows-build`
  dependencies because PyInstaller and FasterWhisper are not required for this
  source-checkout Shell operation.
- Do not install optional ASR, Windows-build, cloud/provider, model or
  credential packages in this operation.
- Do not modify PATH, file associations, the registry or machine/user Python.

## Procedure

1. Verify the base interpreter is a regular file and reports Python 3.11 or
   later.
2. Verify the exact environment path does not already exist. Never reuse or
   overwrite an unknown environment.
3. Create the isolated environment:

   ```text
   <base-python> -m venv E:\BAI_AI\envs\bvp-native-0.22.0
   ```

4. Install from the current Product checkout with pip non-interactively:

   ```text
   E:\BAI_AI\envs\bvp-native-0.22.0\Scripts\python.exe
     -m pip install --disable-pip-version-check --no-input
     C:\home\baisound\projects\bai-video-production
   ```

5. Verify imports and versions without running a Provider:

   ```text
   <venv-python> -c "import ai_video_production,jsonschema; print('PASS')"
   <venv-python> -m pip check
   ```

6. Use the environment only for BAI VIDEO PRODUCTION native verification. The
   ComfyUI process remains the separate loopback-only runtime documented in
   `comfyui-flux-schnell-installation-2026-08-21.md`.

7. Before the native Shell gate, verify that `pywebview` is absent or already
   exactly `6.2.1`. If absent, install only the pinned Product dependency:

   ```text
   E:\BAI_AI\envs\bvp-native-0.22.0\Scripts\python.exe
     -m pip install --disable-pip-version-check --no-input pywebview==6.2.1
   ```

8. Run `pip check`, import `webview`, and report its version before launching
   the Shell. Do not use this step to install or update WebView2, a browser,
   PyInstaller, FasterWhisper, a Provider runtime or a model.

## Failure and rollback

- If creation or installation fails, preserve the pip error output and stop.
- Do not fall back to a system-wide install or the ComfyUI embedded Python.
- A failed newly created environment may be renamed to an inactive diagnostic
  sibling. Deletion is not part of this procedure.
- Reinstalling or upgrading an existing environment requires a new exact
  review; this procedure authorizes only first creation at the fixed path.

## Verification record

- Base Python: `3.12.13`
- Environment created:
  `E:\BAI_AI\envs\bvp-native-0.22.0 — PASS`
- Product `0.22.0` import: `PASS`
- Built Product wheel SHA-256:
  `69c85a52a1a5dc04e51642991d2edff2317e0ffe501fda1ee21379839a3d8f80`
- jsonschema version: `4.26.0`
- pip check: `No broken requirements found — PASS`
- Provider dispatch count during installation: `0`
- Paid/cloud call count: `0`

### Native Shell dependency record

- Requested dependency: `pywebview==6.2.1`
- Target: the same isolated Product environment only
- WebView2/system/browser installation or update: `NOT_AUTHORIZED_BY_THIS_STEP`
- Installed version: `6.2.1 — PASS`
- `import webview`: `PASS`
- Post-install pip check: `No broken requirements found — PASS`
- Provider dispatch count during Shell dependency installation: `0`
- Paid/cloud call count: `0`
