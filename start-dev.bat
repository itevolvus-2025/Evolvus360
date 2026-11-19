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
if not exist .env (
    echo ERROR: backend .env is missing. Copy .env.example to .env and configure it.
    pause
    exit /b 1
)
set "REQUIRED_PACKAGES=fastapi uvicorn sqlalchemy psycopg psycopg-binary alembic pydantic pydantic-settings python-jose pwdlib python-multipart email-validator python-decouple pytest httpx ruff colorama httptools python-dotenv PyYAML watchfiles websockets"
call :ensure_python_environment requirements.txt "%REQUIRED_PACKAGES%"
if errorlevel 1 (
    pause
    exit /b 1
)
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
exit /b %ERRORLEVEL%

:run_email
cd /d "%ROOT%email-service"
if not exist .env (
    echo ERROR: email-service .env is missing. Copy .env.example to .env and configure it.
    pause
    exit /b 1
)
set "REQUIRED_PACKAGES=fastapi uvicorn sqlalchemy psycopg psycopg-binary alembic pydantic pydantic-settings email-validator cryptography python-multipart pytest httpx ruff colorama httptools python-dotenv PyYAML watchfiles websockets"
call :ensure_python_environment requirements.txt "%REQUIRED_PACKAGES%"
if errorlevel 1 (
    pause
    exit /b 1
)
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
exit /b %ERRORLEVEL%

:ensure_python_environment
set "REQUIREMENTS_FILE=%~1"
set "REQUIRED_PACKAGES=%~2"
if not exist .venv\Scripts\python.exe (
    echo Python virtual environment not found. Creating .venv...
    where py >nul 2>&1
    if not errorlevel 1 (
        py -3 -m venv .venv
        if errorlevel 1 (
            echo Python Launcher could not create the environment; trying python...
            where python >nul 2>&1
            if errorlevel 1 (
                echo ERROR: Install Python 3 and add py.exe or python.exe to PATH.
                exit /b 1
            )
            python -m venv .venv
        )
    ) else (
        where python >nul 2>&1
        if errorlevel 1 (
            echo ERROR: Install Python 3 and add py.exe or python.exe to PATH.
            exit /b 1
        )
        python -m venv .venv
    )
    if errorlevel 1 (
        echo ERROR: Could not create the Python virtual environment.
        exit /b 1
    )
) else (
    echo Existing Python virtual environment found; keeping it.
)

.venv\Scripts\python.exe -m pip show %REQUIRED_PACKAGES% >nul 2>&1
if errorlevel 1 (
    echo Required Python packages are missing. Installing from %REQUIREMENTS_FILE%...
    .venv\Scripts\python.exe -m pip install -r "%REQUIREMENTS_FILE%"
    if errorlevel 1 (
        echo ERROR: Python dependency installation failed. Review the pip output above.
        exit /b 1
    )
) else (
    .venv\Scripts\python.exe -m pip check >nul 2>&1
    if errorlevel 1 (
        echo Python dependencies are incomplete. Installing from %REQUIREMENTS_FILE%...
        .venv\Scripts\python.exe -m pip install -r "%REQUIREMENTS_FILE%"
        if errorlevel 1 (
            echo ERROR: Python dependency installation failed. Review the pip output above.
            exit /b 1
        )
    ) else (
        echo Python requirements are already installed; skipping installation.
    )
)
exit /b 0

:run_frontend
cd /d "%ROOT%frontend"
if not exist package-lock.json (
    echo ERROR: frontend package-lock.json is missing; this project uses npm.
    pause
    exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
    echo ERROR: npm is not available on PATH. Install Node.js and reopen the terminal.
    pause
    exit /b 1
)
npm ls --depth=0 >nul 2>&1
if errorlevel 1 (
    if not exist node_modules (
        echo Frontend dependencies are missing. Installing from package-lock.json...
        npm ci
    ) else (
        echo Frontend dependencies are incomplete. Installing missing packages...
        npm install
    )
    if errorlevel 1 (
        echo ERROR: Frontend dependency installation failed. Review the npm output above.
        pause
        exit /b 1
    )
) else (
    echo Frontend dependencies are already installed; skipping installation.
)
npm start
exit /b %ERRORLEVEL%
