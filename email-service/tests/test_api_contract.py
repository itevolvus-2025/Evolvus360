from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models.email import EmailTemplate


def test_health_is_public_and_uses_response_envelope():
    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


def test_send_requires_a_valid_service_key():
    response = TestClient(app).post(
        "/api/v1/emails/send",
        headers={"X-API-Key": "invalid"},
        json={
            "application_name": "EVOLVUS_HRMS",
            "to": ["user@example.com"],
            "template_key": "EMPLOYEE_INVITATION",
            "variables": {},
        },
    )
    assert response.status_code in {401, 503}
    assert response.json()["data"] is None


def test_template_send_is_idempotent_and_records_delivery(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def db_override():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = db_override
    with factory() as db:
        db.add(
            EmailTemplate(
                template_key="GENERAL_NOTIFICATION",
                name="Notification",
                subject="Hello $name",
                body_text="Hello $name",
                required_variables=["name"],
                is_active=True,
                allow_custom_subject=False,
            )
        )
        db.commit()

    monkeypatch.setenv("EMAIL_SERVICE_API_KEY", "test-key")
    payload_key = Fernet.generate_key().decode()
    service_settings = type(
        "Settings",
        (),
        {
            "email_service_api_key": SecretStr("test-key"),
            "email_payload_encryption_key": SecretStr(payload_key),
            "smtp_from_email": "noreply@example.com",
            "app_env": "development",
            "max_retries": 3,
        },
    )()
    monkeypatch.setattr("app.core.security.get_settings", lambda: service_settings)
    monkeypatch.setattr(
        "app.services.email_service.get_settings", lambda: service_settings
    )
    calls = []
    monkeypatch.setattr(
        "app.services.smtp_provider.send_message",
        lambda **kwargs: (
            calls.append(kwargs) or ("noreply@example.com", "<message-id>")
        ),
    )
    client = TestClient(app)
    request = {
        "application_name": "EVOLVUS_HRMS",
        "to": ["user@example.com"],
        "template_key": "GENERAL_NOTIFICATION",
        "variables": {"name": "User"},
    }
    headers = {"X-API-Key": "test-key", "Idempotency-Key": "stable-test-key"}
    first = client.post("/api/v1/emails/send", headers=headers, json=request)
    second = client.post("/api/v1/emails/send", headers=headers, json=request)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()
    assert first.status_code == 202
    assert first.json()["data"]["status"] == "SENT"
    assert second.json()["data"]["idempotent_replay"] is True
    assert len(calls) == 1
