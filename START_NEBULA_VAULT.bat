@echo off
setlocal EnableExtensions
title Nebula Vault Platform - Local Launcher
cd /d "%~dp0"

echo.
echo  ============================================================
echo       NEBULA VAULT PLATFORM - ONE-CLICK LOCAL SETUP
echo  ============================================================
echo.

if not exist "manage.py" (
    echo [ERROR] manage.py was not found.
    echo Extract the complete repository and run this file from its root folder.
    goto :fail
)

set "PY="
where py >nul 2>&1
if not errorlevel 1 (
    py -3.13 --version >nul 2>&1 && set "PY=py -3.13"
    if not defined PY py -3.12 --version >nul 2>&1 && set "PY=py -3.12"
    if not defined PY py -3.11 --version >nul 2>&1 && set "PY=py -3.11"
)

if not defined PY (
    where python >nul 2>&1
    if not errorlevel 1 (
        python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
        if not errorlevel 1 set "PY=python"
    )
)

if not defined PY (
    echo [ERROR] Python 3.11 or newer was not found.
    echo Install Python 3.11+ from https://www.python.org/downloads/windows/
    echo During installation, enable the Python Launcher or Add Python to PATH.
    goto :fail
)

echo [1/5] Python detected:
%PY% --version
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [2/5] Creating virtual environment...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Could not create the virtual environment.
        goto :fail
    )
) else (
    echo [2/5] Reusing existing virtual environment...
)

echo.
echo [3/5] Installing/updating project dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] pip could not be updated.
    goto :fail
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Dependency installation failed. Check your internet connection.
    goto :fail
)

echo.
echo [4/5] Preparing PostgreSQL database and local configuration...
".venv\Scripts\python.exe" "scripts\setup_database.py"
if errorlevel 1 goto :fail

echo.
echo Applying database migrations...
".venv\Scripts\python.exe" manage.py migrate --noinput
if errorlevel 1 (
    echo [ERROR] Database migrations failed.
    goto :fail
)

echo.
echo [5/5] Starting the local website...
echo.
echo Website: http://127.0.0.1:8000/
echo Keep this window open while using the site.
echo Press Ctrl+C to stop the server.
echo.
start "" http://127.0.0.1:8000/
".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000
goto :eof

:fail
echo.
echo Setup did not finish. Review the error above.
pause
exit /b 1
