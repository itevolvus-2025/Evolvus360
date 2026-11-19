# Evolvus360 services

The repository contains independently managed backend processes:

- `backend/`: HRMS FastAPI application, normally port 8000.
- `email-service/`: centralized FastAPI email service, port 8001 with its own PostgreSQL database and Alembic history.
- `frontend/`: Angular UI. The browser calls HRMS only; server-side HRMS calls the email API.

## Start all applications

Double-click `start-dev.bat` in the project root, or run it from PowerShell:

```powershell
.\start-dev.bat
```

It opens separate terminal windows for HRMS (port 8000), Email Service (port
8001), and the Angular frontend (port 4200). It reuses existing Python
environments, creates a missing `.venv`, and installs a service's requirements
only when required packages are missing or inconsistent. It verifies the
frontend packages and installs them from the existing npm lockfile only when
needed. Existing environments are never recreated. If a port is already
listening, that app is skipped to avoid a duplicate process. Each window stays
open so startup errors and logs remain visible.

Stop an app with `Ctrl+C` in its own window. Close that window after the server
has stopped. Closing all three windows stops the local development processes.

Before starting, create each service `.env` from its `.env.example` and set
local configuration. Python and frontend dependencies are installed
automatically when missing. Python 3, Node.js/npm, and network access are needed
for initial setup.

## Centralized database migrations

From the project root run:

```powershell
python db-migrate
```

The script verifies both service configurations connect to the same database,
then upgrades HRMS to head followed by Email Service to head. It prints the
current and final revision for each service and stops on the first failure.
It never drops or resets the database and never changes a version table
directly.

The services share the `Evolvus360` PostgreSQL database but keep independent
migration state: HRMS uses `alembic_version`; Email Service uses
`email_service_alembic_version`. Each Alembic run uses that service's own
virtual environment, settings, models, configuration, and migration directory.

Run an individual service migration only when necessary, from that service
directory and with its own virtual environment:

```powershell
cd D:\EU\Evolvus360\backend
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head

cd D:\EU\Evolvus360\email-service
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
```

These commands only advance the service's own version table. Review pending
migration files before applying changes to a database containing important
data.

## Troubleshooting startup

- A port is reported as already listening: check the matching app terminal or
  stop the existing process before starting another copy.
- A backend terminal cannot create `.venv`: install Python 3 and ensure `py`
  or `python` is available on `PATH`.
- A backend reports missing configuration: copy that service's
  `.env.example` to `.env` and configure its local values. Keep `.env` files
  private and out of source control.
- Dependency installation fails: check network access, Python/pip or npm
  availability, and read the error in that app's terminal.
- A server exits immediately: read the error in its own window; check its
  Python dependencies, `.env`, and required database/service connectivity.
- Migration fails: the command names the failing service and returns non-zero.
  Resolve the reported issue, inspect that service's migration state, then
  rerun the centralized command. Do not reset or manually edit version tables.

## Start and stop separately (PowerShell)

Start HRMS in one terminal:

```powershell
cd D:\EU\Evolvus360\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Start Email Service in a separate terminal:

```powershell
cd D:\EU\Evolvus360\email-service
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Stop either process with `Ctrl+C` in its own terminal. Check email liveness/readiness:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/v1/health
Invoke-RestMethod http://127.0.0.1:8001/api/v1/ready -Headers @{ 'X-API-Key' = $env:EMAIL_SERVICE_API_KEY }
```

Email Service installation, migrations, templates, authentication and API details are documented in [email-service/README.md](email-service/README.md). Each application uses its own `.env`, database URL, process, and migration configuration. Do not commit `.env` files.
