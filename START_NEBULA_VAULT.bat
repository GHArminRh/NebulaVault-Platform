@echo off
setlocal
title Nebula Vault - Local Setup

cd /d "%~dp0"
echo.
echo ==========================================
echo      Nebula Vault - Local Launcher
echo ==========================================
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
  echo Python is installed, but no supported version was detected.
  echo Open PowerShell and run: py --list
  pause
  exit /b 1
)

echo Detected Python version:
%PYTHON_CMD% --version
echo.

if not exist ".venv\Scripts\python.exe" (
  echo [1/4] Creating Python virtual environment...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 (
    echo ERROR: Could not create virtual environment.
    pause
    exit /b 1
  )
) else (
  echo [1/4] Virtual environment already exists.
)

echo [2/4] Installing/updating Python dependencies...
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

echo [3/4] Preparing PostgreSQL and Django...
".venv\Scripts\python.exe" run_local.py
if errorlevel 1 (
  echo.
  echo Nebula Vault could not start. Read the error above.
  pause
  exit /b 1
)

endlocal
