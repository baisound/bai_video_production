@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if not "%~1"=="" (
  echo [ERROR] Unknown argument: %~1
  goto :help_error
)

if /I not "%OS%"=="Windows_NT" (
  echo [ERROR] This build must run on Windows.
  exit /b 2
)

if defined BVP_BUILD_PYTHON (
  set "PYTHON_EXE=%BVP_BUILD_PYTHON%"
) else if exist ".venv\Scripts\python.exe" (
  set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
) else (
  set "PYTHON_EXE=python"
)

for /f %%I in ('powershell.exe -NoProfile -Command "'task048-build-' + [Guid]::NewGuid().ToString('N')"') do set "TASK048_BUILD_OPERATION=%%I"
if not defined TASK048_BUILD_OPERATION exit /b 4
if defined BVP_TASK048_BUILD_ROOT (
  set "TASK048_BUILD_ROOT=%BVP_TASK048_BUILD_ROOT%"
) else (
  set "TASK048_BUILD_ROOT=%CD%\builds"
)
set "TASK048_SYSTEM_TEMP=%TEMP%"
set "TASK048_RUNTIME_ROOT=%TASK048_SYSTEM_TEMP%\%TASK048_BUILD_OPERATION%"
powershell.exe -NoProfile -File "%CD%\native\task047_obs_voice_capture\scripts\build-controller.ps1" -PrepareShellBuild -BuildRoot "%TASK048_BUILD_ROOT%" -RuntimeRoot "%TASK048_RUNTIME_ROOT%" -OperationId "%TASK048_BUILD_OPERATION%"
if errorlevel 1 exit /b 4
set "TMP=%TASK048_RUNTIME_ROOT%"
set "TEMP=%TASK048_RUNTIME_ROOT%"
set "PYTHONDONTWRITEBYTECODE=1"
set "PYINSTALLER_CONFIG_DIR=%TASK048_RUNTIME_ROOT%\pyinstaller-config"
set "HF_HUB_OFFLINE=1"
set "HF_HUB_DISABLE_TELEMETRY=1"
set "HF_HOME=%TASK048_RUNTIME_ROOT%\hf-cache"
"%PYTHON_EXE%" -B -c "import PyInstaller, webview, faster_whisper" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Windows build dependencies are missing for: %PYTHON_EXE%
  echo Install them explicitly, then run this batch again:
  echo   "%PYTHON_EXE%" -m pip install -e ".[windows-build]"
  exit /b 3
)

set "TASK059_HELPER_DIST=%TASK048_BUILD_ROOT%\work\task059-helper-dist"
set "TASK059_HELPER_WORK=%TASK048_BUILD_ROOT%\work\task059-helper-work"
set "TASK059_HELPER_EXE=%TASK059_HELPER_DIST%\BAI Video Production Key Helper.exe"
set "TASK059_BUNDLED_HELPER=%TASK048_BUILD_ROOT%\BAI Video Production\BAI Video Production Key Helper.exe"
set "TASK059_GENERATED_IDENTITY=%TASK048_BUILD_ROOT%\work\task036_shell\task059-generated\_bvp_task059_packaged_helper_identity.py"

echo [INFO] Python: %PYTHON_EXE%
echo [INFO] Building the internal TASK-059 one-attempt key helper...
"%PYTHON_EXE%" -m PyInstaller --distpath "%TASK059_HELPER_DIST%" --workpath "%TASK059_HELPER_WORK%" "%CD%\packaging\task059_ppk_helper.spec"
if errorlevel 1 (
  echo [ERROR] TASK-059 packaged helper build failed.
  exit /b 5
)
if not exist "%TASK059_HELPER_EXE%" (
  echo [ERROR] Helper build finished but the expected internal EXE is missing.
  exit /b 6
)

echo [INFO] Building the private TASK-048 meter worker...
"%PYTHON_EXE%" -m PyInstaller --distpath "%TASK048_BUILD_ROOT%\meter-worker-dist" --workpath "%TASK048_BUILD_ROOT%\meter-worker-work" "%CD%\packaging\task048_meter_worker.spec"
if errorlevel 1 exit /b 13
set "BVP_TASK048_WORKER_BUNDLE=%TASK048_BUILD_ROOT%\meter-worker-dist\BAI Meter Worker"
set "TEMP=%TASK048_SYSTEM_TEMP%"
set "TMP=%TASK048_SYSTEM_TEMP%"
powershell.exe -NoProfile -File "%CD%\native\task047_obs_voice_capture\scripts\build-controller.ps1" -BuildRoot "%TASK048_BUILD_ROOT%" -RuntimeRoot "%TASK048_RUNTIME_ROOT%" -OperationId "%TASK048_BUILD_OPERATION%" -MeterWorkerBundle "%BVP_TASK048_WORKER_BUNDLE%"
if errorlevel 1 exit /b 14
set "TEMP=%TASK048_RUNTIME_ROOT%"
set "TMP=%TASK048_RUNTIME_ROOT%"
set "BVP_TASK048_CONTROLLER_EXE=%TASK048_BUILD_ROOT%\meter-controller\bai-voice-capture-controller.exe"
set "BVP_TASK059_HELPER_EXE=%TASK059_HELPER_EXE%"
echo [INFO] Building the existing TASK-036 one-dir Windows shell...
"%PYTHON_EXE%" -m PyInstaller --distpath "%TASK048_BUILD_ROOT%" --workpath "%TASK048_BUILD_ROOT%\work" "%CD%\packaging\task036_shell.spec"
set "TASK036_BUILD_EXIT=%ERRORLEVEL%"
set "BVP_TASK059_HELPER_EXE="
set "BVP_TASK048_CONTROLLER_EXE="
set "BVP_TASK048_WORKER_BUNDLE="
if not "%TASK036_BUILD_EXIT%"=="0" (
  echo [ERROR] PyInstaller failed.
  exit /b 7
)

if not exist "%TASK048_BUILD_ROOT%\BAI Video Production\BAI Video Production.exe" (
  echo [ERROR] Build command finished but the expected EXE is missing.
  exit /b 8
)
if not exist "%TASK059_BUNDLED_HELPER%" (
  echo [ERROR] Build command finished but the internal helper is missing.
  exit /b 9
)

"%PYTHON_EXE%" "%CD%\tools\windows\verify-task059-packaged-helper.py" "%TASK059_HELPER_EXE%" "%TASK059_BUNDLED_HELPER%" "%TASK059_GENERATED_IDENTITY%"
if errorlevel 1 (
  exit /b 10
)

"%TASK059_BUNDLED_HELPER%" --protocol-version 1 <nul >nul 2>nul
if errorlevel 1 (
  echo [ERROR] TASK-059 helper empty-input native smoke failed.
  exit /b 11
)
"%TASK059_BUNDLED_HELPER%" --protocol-version 0 <nul >nul 2>nul
set "TASK059_INVALID_VERSION_EXIT=%ERRORLEVEL%"
if not "%TASK059_INVALID_VERSION_EXIT%"=="64" (
  echo [ERROR] TASK-059 helper invalid-version refusal failed.
  exit /b 12
)
echo [PASS] TASK-059 helper native smoke passed.

echo [PASS] Windows client build completed:
echo   %TASK048_BUILD_ROOT%\BAI Video Production\BAI Video Production.exe
echo   %TASK059_BUNDLED_HELPER%
exit /b 0

:help
echo Usage: build-windows-exe.bat
echo.
echo Builds the existing TASK-036 one-dir Windows client into .\builds.
echo A fresh contained BVP_TASK048_BUILD_ROOT may override the default output.
echo Existing build output is never overwritten; choose a fresh run directory.
echo Python selection order:
echo   1. BVP_BUILD_PYTHON
echo   2. .venv\Scripts\python.exe
echo   3. python on PATH
echo This command never installs dependencies, signs, tags, releases, or deploys.
echo It builds one internal key helper and runs a secret-free empty-input smoke.
echo The helper is not a second user entrypoint.
exit /b 0

:help_error
echo Run build-windows-exe.bat --help for usage.
exit /b 1
