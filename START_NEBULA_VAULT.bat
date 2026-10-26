@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Nebula Vault - Launcher

cd /d "%~dp0"
echo.
echo ==========================================
echo      Nebula Vault - Launcher
echo ==========================================
echo.
echo The signing key will be requested securely; it will not be saved to a file.
echo.
set "NEBULA_LICENSE_SIGNING_PRIVATE_KEY="
for /f "usebackq delims=" %%K in (`powershell -NoProfile -Command "$s=Read-Host 'Enter NEBULA_LICENSE_SIGNING_PRIVATE_KEY' -AsSecureString; $p=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($s); try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($p) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($p) }"`) do set "NEBULA_LICENSE_SIGNING_PRIVATE_KEY=%%K"
if not defined NEBULA_LICENSE_SIGNING_PRIVATE_KEY (
  echo ERROR: No signing key was entered. Startup cancelled.
  pause
  exit /b 1
)
echo Signing key received. It will be available only to this launcher and its child processes.
echo.

set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
  where python >nul 2>nul
  if not errorlevel 1 (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
  )
)

if not defined PYTHON_CMD (
  echo ERROR: Python 3.11 or newer could not be found.
  echo Install a supported Python version and try again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating Python virtual environment for the first time...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 (
    echo ERROR: Could not create virtual environment.
    pause
    exit /b 1
  )
  set "NEW_VENV=1"
) else (
  echo [1/3] Virtual environment found.
  set "NEW_VENV=0"
)

if not exist "requirements.txt" (
  echo ERROR: requirements.txt was not found.
  pause
  exit /b 1
)

set "REQ_HASH="
for /f "delims=" %%H in ('powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 -LiteralPath requirements.txt).Hash"') do set "REQ_HASH=%%H"
if not defined REQ_HASH (
  echo ERROR: Could not check the dependency list.
  pause
  exit /b 1
)

set "INSTALL_DEPS=0"
if "!NEW_VENV!"=="1" set "INSTALL_DEPS=1"
if not exist ".venv\requirements.sha256" set "INSTALL_DEPS=1"
if exist ".venv\requirements.sha256" (
  set "OLD_REQ_HASH="
  set /p "OLD_REQ_HASH="<".venv\requirements.sha256"
  if not "!OLD_REQ_HASH!"=="!REQ_HASH!" set "INSTALL_DEPS=1"
)

if "!INSTALL_DEPS!"=="1" (
  echo [2/3] Installing dependencies because this is the first setup or requirements.txt changed...
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  if errorlevel 1 (
    echo ERROR: pip upgrade failed. Check your internet connection.
    pause
    exit /b 1
  )
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo ERROR: Dependency installation failed.
    pause
    exit /b 1
  )
  >".venv\requirements.sha256" echo !REQ_HASH!
) else (
  echo [2/3] Dependencies are up to date. Skipping installation.
)

echo [3/3] Checking configuration and starting Nebula Vault...
".venv\Scripts\python.exe" run_local.py
if errorlevel 1 (
  echo.
  echo Nebula Vault could not start. Read the error above.
  pause
  exit /b 1
)

endlocal
