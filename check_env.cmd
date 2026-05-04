@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

cd /d "%~dp0"

echo.
echo [Windows Server Monitor] Checking runtime environment...
echo.

call :find_python
if not defined PYTHON_CMD (
    echo [WARN] Python was not found.
    call :install_python
    call :find_python
)

if not defined PYTHON_CMD (
    echo.
    echo [ERROR] Python is still unavailable.
    echo Please install Python 3.10+ manually, then run this script again:
    echo https://www.python.org/downloads/windows/
    echo.
    call :maybe_pause
    exit /b 1
)

echo [OK] Python command: %PYTHON_CMD%
%PYTHON_CMD% --version

if not exist "requirements.txt" (
    echo.
    echo [ERROR] requirements.txt was not found in this folder.
    call :maybe_pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [INFO] Creating virtual environment: .venv
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        call :maybe_pause
        exit /b 1
    )
) else (
    echo [OK] Virtual environment already exists: .venv
)

echo.
echo [INFO] Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo [WARN] pip upgrade failed. Continuing with the existing pip version.
)

echo.
echo [INFO] Installing required packages...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Dependency installation failed.
    call :maybe_pause
    exit /b 1
)

echo.
echo [INFO] Verifying imports...
".venv\Scripts\python.exe" -c "import fastapi, uvicorn, psutil; print('fastapi/uvicorn/psutil OK')"
if errorlevel 1 (
    echo.
    echo [ERROR] Python packages are incomplete.
    call :maybe_pause
    exit /b 1
)

echo.
echo [OK] Environment is ready.
echo You can now run start_monitor.cmd
echo.
call :maybe_pause
exit /b 0

:find_python
set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_CMD=py -3"
        exit /b 0
    )
)

where python >nul 2>nul
if not errorlevel 1 (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_CMD=python"
        exit /b 0
    )
)
exit /b 0

:install_python
where winget >nul 2>nul
if errorlevel 1 (
    echo [WARN] winget was not found, so Python cannot be installed automatically.
    exit /b 1
)

echo [INFO] Trying to install Python 3.12 with winget...
winget install -e --id Python.Python.3.12 --source winget --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
    echo [WARN] winget failed to install Python.
    exit /b 1
)

echo [INFO] Python installer finished. Refreshing command lookup...
exit /b 0

:maybe_pause
if /i "%MONITOR_NO_PAUSE%"=="1" exit /b 0
pause
exit /b 0
