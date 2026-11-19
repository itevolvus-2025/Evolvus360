@echo off
setlocal
set "ROOT=%~dp0"

if /i "%~1"=="hrms" goto run_hrms
if /i "%~1"=="email" goto run_email
if /i "%~1"=="frontend" goto run_frontend

call :start_service "HRMS Backend" "8000" "%ROOT%backend" hrms
call :start_service "Email Service" "8001" "%ROOT%email-service" email
call :start_service "Frontend" "4200" "%ROOT%frontend" frontend
echo Startup requests sent. Each app has its own terminal window.
exit /b 0

:start_service
set "TITLE=%~1"
set "PORT=%~2"
set "APP_DIR=%~3"
set "APP_MODE=%~4"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$listener = Get-NetTCPConnection -LocalPort %PORT% -State Listen -ErrorAction SilentlyContinue; if ($listener) { exit 10 } else { exit 0 }"
if errorlevel 1 (
    echo Skipping %TITLE%: port %PORT% is already listening. Check that application's terminal before starting another copy.
) else (
    echo Starting %TITLE% on port %PORT%...
    start "%TITLE%" /D "%APP_DIR%" "%ComSpec%" /k call "%ROOT%start-dev.bat" %APP_MODE%
)
exit /b 0

:run_hrms
cd /d "%ROOT%backend"
if not exist .venv\Scripts\python.exe (
    echo ERROR: backend virtual environment is missing. Create it and install requirements.txt.
    pause
    exit /b 1
)
if not exist .env (
    echo ERROR: backend .env is missing. Copy .env.example to .env and configure it.
    pause
    exit /b 1
)
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
exit /b %ERRORLEVEL%

:run_email
cd /d "%ROOT%email-service"
if not exist .venv\Scripts\python.exe (
    echo ERROR: email-service virtual environment is missing. Create it and install requirements.txt.
    pause
    exit /b 1
)
if not exist .env (
    echo ERROR: email-service .env is missing. Copy .env.example to .env and configure it.
    pause
    exit /b 1
)
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
exit /b %ERRORLEVEL%

:run_frontend
cd /d "%ROOT%frontend"
if not exist package-lock.json (
    echo ERROR: frontend package-lock.json is missing; this project uses npm.
    pause
    exit /b 1
)
if not exist node_modules (
    echo ERROR: frontend dependencies are missing. Run npm ci in this directory.
    pause
    exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
    echo ERROR: npm is not available on PATH. Install Node.js and reopen the terminal.
    pause
    exit /b 1
)
npm start
exit /b %ERRORLEVEL%
