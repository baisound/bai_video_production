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

"%PYTHON_EXE%" -c "import PyInstaller, webview, faster_whisper" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Windows build dependencies are missing for: %PYTHON_EXE%
  echo Install them explicitly, then run this batch again:
  echo   "%PYTHON_EXE%" -m pip install -e ".[windows-build]"
  exit /b 3
)

if not exist "builds" mkdir "builds"
if errorlevel 1 (
  echo [ERROR] Could not create: %CD%\builds
  exit /b 4
)

echo [INFO] Python: %PYTHON_EXE%
echo [INFO] Building the existing TASK-036 one-dir Windows shell...
"%PYTHON_EXE%" -m PyInstaller --noconfirm --clean --distpath "%CD%\builds" --workpath "%CD%\builds\work" "%CD%\packaging\task036_shell.spec"
if errorlevel 1 (
  echo [ERROR] PyInstaller failed.
  exit /b 5
)

if not exist "builds\BAI Video Production\BAI Video Production.exe" (
  echo [ERROR] Build command finished but the expected EXE is missing.
  exit /b 6
)

echo [PASS] Windows client build completed:
echo   %CD%\builds\BAI Video Production\BAI Video Production.exe
exit /b 0

:help
echo Usage: build-windows-exe.bat
echo.
echo Builds the existing TASK-036 one-dir Windows client into .\builds.
echo Python selection order:
echo   1. BVP_BUILD_PYTHON
echo   2. .venv\Scripts\python.exe
echo   3. python on PATH
echo This command never installs dependencies, signs, tags, releases, or deploys.
exit /b 0

:help_error
echo Run build-windows-exe.bat --help for usage.
exit /b 1
