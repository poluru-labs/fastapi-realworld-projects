from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, register_headers

Q1 = {
    "period_start": "2026-01-01T00:00:00+00:00",
    "period_end": "2026-03-31T23:59:59+00:00",
}


def test_admin_metrics_and_generate_sales_summary(client: TestClient) -> None:
    headers = admin_headers(client)
    metrics = client.get("/api/v1/reports/metrics", headers=headers)
    assert metrics.status_code == 200
    assert len(metrics.json()) == 5

    generated = client.post(
        "/api/v1/reports/runs",
        headers=headers,
        json={"template_id": 1, **Q1},
    )
    assert generated.status_code == 201
    body = generated.json()
    assert body["status"] == "completed"
    result = body["result"]
    assert result["kind"] == "sales_summary"
    assert result["row_count"] == 5
    assert result["sections"][0]["grand_total"] == 5590.5


def test_non_admin_cannot_list_metrics(client: TestClient) -> None:
    headers = register_headers(client, "analyst@example.com")
    assert client.get("/api/v1/reports/metrics", headers=headers).status_code == 403


def test_user_cannot_read_other_run(client: TestClient) -> None:
    admin = admin_headers(client)
    run = client.post(
        "/api/v1/reports/runs",
        headers=admin,
        json={"template_id": 1, **Q1},
    ).json()

    other = register_headers(client, "other@example.com")
    assert client.get(f"/api/v1/reports/runs/{run['id']}", headers=other).status_code == 404


def test_create_template_and_ledger_run(client: TestClient) -> None:
    headers = register_headers(client, "builder@example.com")
    template = client.post(
        "/api/v1/templates",
        headers=headers,
        json={"name": "My ledger", "kind": "activity_ledger"},
    )
    assert template.status_code == 201
    template_id = template.json()["id"]

    run = client.post(
        "/api/v1/reports/runs",
        headers=headers,
        json={"template_id": template_id, **Q1},
    )
    assert run.status_code == 201
    assert run.json()["result"]["kind"] == "activity_ledger"
    assert len(run.json()["result"]["sections"][0]["rows"]) == 5
