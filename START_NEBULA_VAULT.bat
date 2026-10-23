@echo off
setlocal
title Nebula Vault - Local Setup

cd /d "%~dp0"
echo.
echo ==========================================
echo      Nebula Vault - Local Launcher
echo ==========================================
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python launcher was not found.
  echo Install Python 3.11 or newer from https://www.python.org/downloads/
  echo During installation, enable the Python launcher and Add Python to PATH.
  pause
  exit /b 1
)

py -3.11 --version >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python 3.11 or newer was not found through the Python launcher.
  echo Install Python 3.11+ from https://www.python.org/downloads/
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/4] Creating Python virtual environment...
  py -3.11 -m venv .venv
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
