@echo off
setlocal EnableExtensions
chcp 65001 >nul

cd /d "%~dp0"

if not exist "server_monitor_api.py" (
    echo [ERROR] server_monitor_api.py was not found.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [WARN] Virtual environment is missing. Running check_env.cmd first...
    set "MONITOR_NO_PAUSE=1"
    call "%~dp0check_env.cmd"
    if errorlevel 1 (
        echo [ERROR] Environment setup failed.
        call :maybe_pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" -c "import fastapi, uvicorn, psutil" >nul 2>nul
if errorlevel 1 (
    echo [WARN] Required packages are missing. Running check_env.cmd first...
    set "MONITOR_NO_PAUSE=1"
    call "%~dp0check_env.cmd"
    if errorlevel 1 (
        echo [ERROR] Environment setup failed.
        call :maybe_pause
        exit /b 1
    )
)

echo.
echo [Windows Server Monitor] Starting API server...
echo.
echo Optional environment variables:
echo   MONITOR_API_KEY=your_secret
echo   MONITOR_PORT=8765
echo   MONITOR_INTERVAL_SECONDS=5
echo   MONITOR_SSL_CERTFILE=certs\fullchain.pem
echo   MONITOR_SSL_KEYFILE=certs\privkey.pem
echo.
echo Config file:
echo   monitor_config.json
echo.
echo Extra command-line arguments passed to this script will be forwarded.
echo Example: start_monitor.cmd --api-key my_secret --port 8765
echo SSL example: start_monitor.cmd --ssl-certfile certs\fullchain.pem --ssl-keyfile certs\privkey.pem
echo.

".venv\Scripts\python.exe" "server_monitor_api.py" %*
set "SERVER_EXIT=%ERRORLEVEL%"

echo.
echo Server stopped with exit code %SERVER_EXIT%.
call :maybe_pause
exit /b %SERVER_EXIT%

:maybe_pause
if /i "%MONITOR_NO_PAUSE%"=="1" exit /b 0
pause
exit /b 0

