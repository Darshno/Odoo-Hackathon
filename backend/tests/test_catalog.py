def register_customer(client):
    response = client.post("/api/auth/register", json={
        "full_name": "Customer", "email": "customer@example.com",
        "password": "StrongPass!1", "confirm_password": "StrongPass!1",
    })
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_staff_can_manage_products_and_plans(client, admin_headers):
    staff = client.post("/api/users/staff", headers=admin_headers, json={
        "full_name": "Staff", "email": "staff@example.com",
        "password": "StrongPass!1", "confirm_password": "StrongPass!1",
    })
    login = client.post("/api/auth/login", json={"email": "staff@example.com", "password": "StrongPass!1"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    product = client.post("/api/products", headers=headers, json={
        "name": "Workspace", "variants": [{"name": "Pro", "sku": "PRO", "price": "12.00"}],
    })
    assert product.status_code == 201
    product_id = product.json()["id"]
    plan = client.post("/api/plans", headers=headers, json={
        "product_id": product_id, "name": "Monthly Pro", "price": "12.00", "billing_interval": "MONTHLY",
    })
    assert plan.status_code == 201
    assert client.get("/api/products", headers=headers).status_code == 200


def test_customer_reads_only_active_catalog_and_cannot_manage(client, admin_headers):
    product = client.post("/api/products", headers=admin_headers, json={"name": "Active"})
    assert product.status_code == 201
    customer_headers = register_customer(client)
    assert client.post("/api/products", headers=customer_headers, json={"name": "Nope"}).status_code == 403
    assert client.get("/api/products", headers=customer_headers).json()["total"] == 1


def test_plan_rejects_variant_from_another_product(client, admin_headers):
    first = client.post("/api/products", headers=admin_headers, json={
        "name": "One", "variants": [{"name": "A", "sku": "A", "price": "1.00"}],
    }).json()
    second = client.post("/api/products", headers=admin_headers, json={"name": "Two"}).json()
    variant_id = first["variants"][0]["id"]
    response = client.post("/api/plans", headers=admin_headers, json={
        "product_id": second["id"], "variant_id": variant_id, "name": "Invalid", "price": "2.00",
    })
    assert response.status_code == 422
