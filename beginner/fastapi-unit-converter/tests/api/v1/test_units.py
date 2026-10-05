from fastapi.testclient import TestClient


def test_list_units(client: TestClient) -> None:
    response = client.get("/api/v1/units")
    assert response.status_code == 200
    data = response.json()
    assert [row["category"] for row in data] == ["temperature", "distance", "weight"]

    temperature = data[0]
    assert temperature["base_unit"] == "celsius"
    assert [unit["code"] for unit in temperature["units"]] == [
        "celsius",
        "fahrenheit",
        "kelvin",
    ]
    assert temperature["units"][0]["factor_to_base"] is None
    assert temperature["units"][0]["aliases"] == ["c", "degc"]

    distance = data[1]
    inch = next(unit for unit in distance["units"] if unit["code"] == "inch")
    assert inch["factor_to_base"] == "0.0254"
    assert distance["base_unit"] == "meter"

    weight = data[2]
    pound = next(unit for unit in weight["units"] if unit["code"] == "pound")
    assert pound["factor_to_base"] == "453.59237"
    assert weight["base_unit"] == "gram"


def test_get_weight_category(client: TestClient) -> None:
    response = client.get("/api/v1/units/weight")
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "weight"
    assert any(unit["code"] == "kilogram" for unit in body["units"])


def test_unknown_category(client: TestClient) -> None:
    response = client.get("/api/v1/units/volume")
    assert response.status_code == 422
