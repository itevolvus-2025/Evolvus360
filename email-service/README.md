# Evolvus360 Central Email Service

An independent FastAPI process for email rendering, SMTP delivery, idempotency, logs, and retries. HRMS and future applications call this service over HTTP; no SMTP settings belong in those applications. It shares the PostgreSQL `Evolvus360` database with HRMS while owning its tables and migration history.

## Local setup (PowerShell)

```powershell
cd D:\EU\Evolvus360\email-service
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Set DATABASE_URL, both API keys, EMAIL_PAYLOAD_ENCRYPTION_KEY and SMTP values in .env
# Set DATABASE_URL to the shared Evolvus360 database in .env.
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.commands.seed_templates
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Stop with `Ctrl+C` in that service terminal. HRMS is a separate terminal/process on its configured port (default 8000); stopping one does not affect the other. HRMS environment requires `EMAIL_SERVICE_BASE_URL=http://127.0.0.1:8001`, `EMAIL_SERVICE_API_KEY` matching the service key, and `EMAIL_SERVICE_TIMEOUT_SECONDS=10`.

## API

All routes are under `/api/v1`. `GET /health` is a liveness check. `GET /ready` checks DB and provider configuration. Service calls use `X-API-Key`; admin operations use `X-Admin-API-Key`. Keep both keys on server-side environments only. In production use HTTPS.

- `POST /emails/send`: template send, recipients/CC/BCC, variables, optional validated attachments; accepts `Idempotency-Key`.
- `GET /emails/{email_id}`: masked status for service callers.
- `GET /emails`: paginated, filterable logs (admin).
- `POST /emails/{email_id}/retry`: retry failed delivery (admin).
- `GET /templates`, `GET /templates/{template_key}`, `POST /templates`, `PUT /templates/{template_key}`, `PATCH /templates/{template_key}/status` (admin).

Example:

```powershell
$headers = @{ 'X-API-Key' = $env:EMAIL_SERVICE_API_KEY; 'Idempotency-Key' = 'hrms-invite-unique-id' }
$body = @{ application_name='EVOLVUS_HRMS'; to=@('person@example.com'); template_key='EMPLOYEE_INVITATION'; variables=@{ employee_name='Jhon Doe'; company_name='Evolvus'; invitation_link='https://example.com/onboarding?token=opaque'; expiry_hours=48 } } | ConvertTo-Json -Depth 8
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8001/api/v1/emails/send -Headers $headers -ContentType 'application/json' -Body $body
```

## Database and templates

The service has its own Alembic configuration, version table (`email_service_alembic_version`), and owns `email_templates`, `email_logs`, `email_delivery_attempts`, and `email_provider_settings`. Apply migrations with `python -m alembic upgrade head`; seed initial reusable templates with `python -m app.commands.seed_templates`. HRMS uses its separate `alembic_version` table. SMTP credentials are environment secrets, never database fields. Templates use `$variable` placeholders; HTML values are escaped and executable template code is unsupported.

## Troubleshooting

- `503` from readiness: verify DB, SMTP host/from address, service/admin keys and Fernet payload key.
- `401`: compare server-side API keys; never put the service key in Angular.
- `FAILED` email: inspect sanitized admin log and attempt count; retry only within configured retry limit.
- HRMS `email_dispatch_status=FAILED`: verify the central service is running and the HRMS key matches; retry the active invitation via `POST /api/v1/users/{user_id}/invite/retry`.
