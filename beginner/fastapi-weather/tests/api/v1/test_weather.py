from fastapi.testclient import TestClient


def test_list_and_current_seed(client: TestClient) -> None:
    listed = client.get("/api/v1/locations")
    assert listed.status_code == 200
    assert len(listed.json()) == 3

    current = client.get("/api/v1/locations/2/current")
    assert current.status_code == 200
    body = current.json()
    assert body["condition"] == "Overcast"
    assert body["location_id"] == 2


def test_forecast_days(client: TestClient) -> None:
    response = client.get("/api/v1/locations/1/forecast")
    assert response.status_code == 200
    days = response.json()
    assert len(days) == 3
    assert days[0]["high_c"] == 19.0
    assert days[2]["precipitation_chance_pct"] == 45


def test_create_patch_and_delete(client: TestClient) -> None:
    created = client.post(
        "/api/v1/locations",
        json={"city": "Austin", "country_code": "US", "region": "Texas"},
    )
    assert created.status_code == 201
    location_id = created.json()["id"]

    patched = client.patch(
        f"/api/v1/locations/{location_id}/current",
        json={"temp_c": 28.0, "condition": "Hot and sunny"},
    )
    assert patched.status_code == 200
    assert patched.json()["temp_c"] == 28.0
    assert patched.json()["condition"] == "Hot and sunny"

    assert client.delete(f"/api/v1/locations/{location_id}").status_code == 204
    assert client.get(f"/api/v1/locations/{location_id}").status_code == 404


def test_search_locations(client: TestClient) -> None:
    response = client.get("/api/v1/locations", params={"q": "tokyo"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["city"] == "Tokyo"


def test_duplicate_location_conflict(client: TestClient) -> None:
    response = client.post(
        "/api/v1/locations",
        json={"city": "London", "country_code": "GB"},
    )
    assert response.status_code == 409
