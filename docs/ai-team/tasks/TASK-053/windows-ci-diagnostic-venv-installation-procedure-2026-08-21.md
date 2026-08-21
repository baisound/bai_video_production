# Windows CI Diagnostic Venv Installation Procedure

Date: 2026-08-21
Scope: repository-local ignored `.venv/` for PR #205 failure reproduction only

## Purpose

PR #205 head `959df03` のGitHub-hosted Windows 3.11/3.12/3.13 runは全testを100%まで実行した後、failure summary前で停止した。test名とtracebackを取得するため、Windows上でserial verbose/first-failure regressionを再現する。

## Isolation boundary

- create only `C:\home\baisound\projects\bai-video-production\.venv`
- source interpreter is the existing isolated Python 3.12 runtime at `E:\BAI_AI\envs\bvp-native-0.22.0\Scripts\python.exe`
- do not modify the source runtime, system Python, PATH, registry, ComfyUI, Ollama or audio runtime
- `.venv/` is already excluded by `.gitignore`
- no paid/cloud/native Provider execution

## Create and install

```text
E:\BAI_AI\envs\bvp-native-0.22.0\Scripts\python.exe -m venv C:\home\baisound\projects\bai-video-production\.venv
C:\home\baisound\projects\bai-video-production\.venv\Scripts\python.exe -m pip install --disable-pip-version-check --no-input -e ".[dev]" pytest-xdist==3.8.0 pytest-timeout==2.4.0
```

## Diagnostic commands

First obtain the earliest deterministic failure without parallel scheduling:

```text
.venv\Scripts\python.exe -m pytest -vv -x --timeout=120
```

After the fix, run the exact hosted parallel contract:

```text
.venv\Scripts\python.exe -m pytest -q -n 2 --dist loadfile --timeout=120 --max-worker-restart=0 --durations=20
```

## Verification and cleanup

Record Python/plugin versions, first failing test, traceback, focused fix result and full parallel result. Keep `.venv/` until PR #205 hosted Windows checks pass. It may then be removed only after resolving the exact path and confirming it remains the ignored repository-local diagnostic directory.

## 2026-08-21 diagnostic result

Installed only in the ignored repository-local `.venv/`:

- Python `3.12.13`
- pytest `9.1.1`
- pytest-xdist `3.8.0`
- pytest-timeout `2.4.0`

The serial reproduction identified two independent Windows failures:

1. `test_journal_temp_name_substitution_never_returns_terminal_success` patched only `os.replace`, while the Windows production path uses `MoveFileExW`. A bounded private helper now provides an exact Windows test seam without changing the production replacement flags or byte-integrity checks.
2. `test_production_transport_rejects_invalid_method_body_combinations` allowed pytest to derive a parameter ID from a 512 KiB oversized bytes fixture. The resulting `PYTEST_CURRENT_TEST` value exceeded the Windows environment-variable limit and also made the failure summary unbounded. The four cases now use short explicit IDs.

Verification:

- Windows focused boundary: `5 passed`
- WSL focused OS boundary: `5 passed`
- Windows full parallel except the native OBS installer acceptance: `2828 passed, 4 skipped`
- changed Python `py_compile`: PASS
- `git diff --check`: PASS

The native OBS installer acceptance was not bypassed or reported as a PASS. Its local run reached the real installer but was denied by the managed environment when writing the Start menu and HKCU uninstall registry. It remains delegated to the clean GitHub-hosted Windows checks, where that test has the required runner boundary. No registry, Start menu, system Python, PATH, ComfyUI, Ollama or audio-runtime change was made by this diagnostic installation procedure.
