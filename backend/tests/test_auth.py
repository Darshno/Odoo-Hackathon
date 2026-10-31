from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.user import PasswordResetToken, User
from app.core.security import hash_reset_token


def register_payload(email="customer@example.com", password="StrongPass!1"):
    return {"full_name": "Jamie Customer", "email": email, "password": password, "confirm_password": password}


def test_registration_creates_customer_and_returns_token(client):
    response = client.post("/api/auth/register", json=register_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["role"] == "CUSTOMER"
    assert body["user"].get("password_hash") is None
    assert body["access_token"]


def test_duplicate_email_is_rejected(client):
    client.post("/api/auth/register", json=register_payload())
    response = client.post("/api/auth/register", json=register_payload())
    assert response.status_code == 409


def test_password_policy_is_enforced(client):
    response = client.post("/api/auth/register", json=register_payload(password="weakpassword"))
    assert response.status_code == 422
    assert "uppercase" in response.json()["detail"]


def test_login_and_me(client):
    registered = client.post("/api/auth/register", json=register_payload())
    token = registered.json()["access_token"]
    login = client.post("/api/auth/login", json={"email": "customer@example.com", "password": "StrongPass!1"})
    assert login.status_code == 200
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "customer@example.com"


def test_invalid_login_and_unauthorized_requests(client):
    client.post("/api/auth/register", json=register_payload())
    assert client.post("/api/auth/login", json={"email": "customer@example.com", "password": "wrong"}).status_code == 401
    assert client.get("/api/profile").status_code == 401
    assert client.get("/api/users").status_code == 401


def test_customer_cannot_access_user_management(client):
    registered = client.post("/api/auth/register", json=register_payload())
    response = client.get("/api/users", headers={"Authorization": f"Bearer {registered.json()['access_token']}"})
    assert response.status_code == 403


def test_forgot_reset_token_is_single_use(client):
    client.post("/api/auth/register", json=register_payload())
    forgot = client.post("/api/auth/forgot-password", json={"email": "customer@example.com"})
    token = forgot.json()["preview_token"]
    reset = {"token": token, "new_password": "NewStrong!2", "confirm_password": "NewStrong!2"}
    assert client.post("/api/auth/reset-password", json=reset).status_code == 200
    assert client.post("/api/auth/reset-password", json=reset).status_code == 400


def test_reset_token_expiry_and_previous_token_invalidation(client, db_session):
    client.post("/api/auth/register", json=register_payload())
    first = client.post("/api/auth/forgot-password", json={"email": "customer@example.com"}).json()["preview_token"]
    second = client.post("/api/auth/forgot-password", json={"email": "customer@example.com"}).json()["preview_token"]
    old_reset = {"token": first, "new_password": "NewStrong!2", "confirm_password": "NewStrong!2"}
    assert client.post("/api/auth/reset-password", json=old_reset).status_code == 400
    row = db_session.scalar(select(PasswordResetToken).where(PasswordResetToken.hashed_token == hash_reset_token(second)))
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()
    expired_reset = {"token": second, "new_password": "NewStrong!2", "confirm_password": "NewStrong!2"}
    assert client.post("/api/auth/reset-password", json=expired_reset).status_code == 400


def test_inactive_account_cannot_login(client, db_session):
    client.post("/api/auth/register", json=register_payload())
    user = db_session.scalar(select(User).where(User.email == "customer@example.com"))
    user.is_active = False
    db_session.commit()
    assert client.post("/api/auth/login", json={"email": "customer@example.com", "password": "StrongPass!1"}).status_code == 401
