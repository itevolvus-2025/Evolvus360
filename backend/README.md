# Evolvus360 backend

The backend uses FastAPI, synchronous SQLAlchemy 2.x sessions, PostgreSQL, and
Alembic. Start with the [database and migration standards](docs/database-migrations.md)
for model conventions, local database configuration, and explicit migration
commands.

Set up the virtual environment and dependencies from `requirements.txt`, copy
`.env.example` to `.env`, then configure `DATABASE_URL`. The application does not
run schema migrations automatically; invoke Alembic explicitly as documented.
