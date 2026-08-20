@echo off
setlocal EnableExtensions
cd /d "%~dp0"
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
"%PYTHON_EXE%" -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] PyInstaller is missing. Run:
  echo   "%PYTHON_EXE%" -m pip install -e ".[windows-build]"
  exit /b 3
)
if not exist "builds" mkdir "builds"
"%PYTHON_EXE%" -m PyInstaller --noconfirm --clean --distpath "%CD%\builds" --workpath "%CD%\builds\work-dbd-training" "%CD%\packaging\task049_training_studio.spec"
if errorlevel 1 exit /b 4
if not exist "builds\BAI DbD Training Studio\BAI DbD Training Studio.exe" (
  echo [ERROR] Expected EXE is missing.
  exit /b 5
)
echo [PASS] %CD%\builds\BAI DbD Training Studio\BAI DbD Training Studio.exe
exit /b 0
