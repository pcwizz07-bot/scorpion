import os
import secrets

from cryptography.fernet import Fernet

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://scorpion:REDACTED_DEV_PASSWORD@127.0.0.1:5432/scorpion",
)
os.environ["PROVISIONING_TOKEN"] = "test-provisioning-token-" + secrets.token_hex(8)
os.environ["CRYPTO_KEY"] = Fernet.generate_key().decode()
os.environ.setdefault("DEDUP_WINDOW_SECONDS", "60")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402, F401
from app.config import settings  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def provisioning_token():
    return settings.PROVISIONING_TOKEN


@pytest.fixture
def registered_device(client, provisioning_token):
    resp = client.post(
        "/api/v1/devices/register",
        json={"name": "test-device", "lat": 1.0, "lng": 2.0},
        headers={"X-Provisioning-Token": provisioning_token},
    )
    assert resp.status_code == 201
    body = resp.json()
    return {"device_id": body["device_id"], "device_token": body["device_token"]}
