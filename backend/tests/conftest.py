import os

os.environ["DATABASE_URL"] = "sqlite:///./test_brightloop.db"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["RESET_PREVIEW_ENABLED"] = "true"
os.environ["BILLING_SCHEDULER_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User, UserRole

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def admin_headers(client):
    db = TestingSessionLocal()
    admin = User(full_name="Admin User", email="admin@example.com", password_hash=hash_password("AdminPass!123"), role=UserRole.ADMIN)
    db.add(admin)
    db.commit()
    db.close()
    response = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "AdminPass!123"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
