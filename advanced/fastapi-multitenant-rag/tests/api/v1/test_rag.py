from fastapi.testclient import TestClient


def test_seed_query_refund(client: TestClient, tenant_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/collections/product-docs/query",
        headers=tenant_headers,
        json={"question": "How long is the refund window?", "top_k": 2},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["collection_slug"] == "product-docs"
    assert body["citations"]
    assert "30" in body["answer"] or "refund" in body["answer"].lower()


def test_tenant_isolation(client: TestClient, tenant_headers: dict[str, str]) -> None:
    other = client.post(
        "/api/v1/auth/register",
        json={
            "email": "other@example.com",
            "password": "SecurePass123!",
            "full_name": "Other User",
            "tenant_name": "Other Co",
            "tenant_slug": "other-co",
        },
    )
    assert other.status_code == 201
    other_headers = {
        "Authorization": f"Bearer {other.json()['tokens']['access_token']}",
        "X-Tenant-Slug": "other-co",
    }
    denied = client.get("/api/v1/collections/product-docs", headers=other_headers)
    assert denied.status_code == 404


def test_ingest_and_list_documents(client: TestClient, tenant_headers: dict[str, str]) -> None:
    created = client.post(
        "/api/v1/collections",
        headers=tenant_headers,
        json={"slug": "hr-handbook", "name": "HR", "description": "Policies"},
    )
    assert created.status_code == 201

    ingest = client.post(
        "/api/v1/collections/hr-handbook/documents",
        headers=tenant_headers,
        json={
            "title": "PTO",
            "text": "Employees receive 20 days of paid time off each calendar year.",
        },
    )
    assert ingest.status_code == 201
    assert ingest.json()["chunk_count"] >= 1

    listed = client.get("/api/v1/collections/hr-handbook/documents", headers=tenant_headers)
    assert listed.status_code == 200
    assert any(row["title"] == "PTO" for row in listed.json())


def test_missing_tenant_header(client: TestClient, tenant_headers: dict[str, str]) -> None:
    headers = {"Authorization": tenant_headers["Authorization"]}
    response = client.get("/api/v1/collections", headers=headers)
    assert response.status_code == 403
