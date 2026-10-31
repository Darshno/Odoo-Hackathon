def test_admin_can_list_filter_and_create_staff(client, admin_headers):
    for index in range(3):
        client.post("/api/auth/register", json={"full_name": f"Customer {index}", "email": f"c{index}@example.com", "password": "StrongPass!1", "confirm_password": "StrongPass!1"})
    listing = client.get("/api/users?page=1&page_size=2&search=Customer", headers=admin_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 3
    assert len(listing.json()["items"]) == 2
    staff = client.post("/api/users/staff", headers=admin_headers, json={"full_name": "Staff User", "email": "staff@example.com", "password": "StaffPass!1", "confirm_password": "StaffPass!1"})
    assert staff.status_code == 201
    assert staff.json()["role"] == "STAFF"
    duplicate = client.post("/api/users/staff", headers=admin_headers, json={"full_name": "Duplicate", "email": "staff@example.com", "password": "StaffPass!1", "confirm_password": "StaffPass!1"})
    assert duplicate.status_code == 409


def test_staff_cannot_access_admin_api(client, admin_headers):
    staff = client.post("/api/users/staff", headers=admin_headers, json={"full_name": "Staff User", "email": "staff@example.com", "password": "StaffPass!1", "confirm_password": "StaffPass!1"})
    login = client.post("/api/auth/login", json={"email": "staff@example.com", "password": "StaffPass!1"})
    assert staff.status_code == 201
    assert client.get("/api/users", headers={"Authorization": f"Bearer {login.json()['access_token']}"}).status_code == 403


def test_admin_cannot_deactivate_self(client, admin_headers):
    me = client.get("/api/auth/me", headers=admin_headers).json()
    response = client.patch(f"/api/users/{me['id']}/status?is_active=false", headers=admin_headers)
    assert response.status_code == 400


def test_customer_profile_is_owned(client):
    registered = client.post("/api/auth/register", json={"full_name": "Customer One", "email": "one@example.com", "password": "StrongPass!1", "confirm_password": "StrongPass!1"})
    token = registered.json()["access_token"]
    update = client.patch("/api/profile", headers={"Authorization": f"Bearer {token}"}, json={"full_name": "Updated Customer"})
    assert update.status_code == 200
    assert update.json()["full_name"] == "Updated Customer"
    assert client.patch("/api/users/999/status?is_active=false", headers={"Authorization": f"Bearer {token}"}).status_code == 403
