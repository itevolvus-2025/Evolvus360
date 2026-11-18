# Evolvus360 services

The repository contains independently managed backend processes:

- `backend/`: HRMS FastAPI application, normally port 8000.
- `email-service/`: centralized FastAPI email service, port 8001 with its own PostgreSQL database and Alembic history.
- `frontend/`: Angular UI. The browser calls HRMS only; server-side HRMS calls the email API.

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
