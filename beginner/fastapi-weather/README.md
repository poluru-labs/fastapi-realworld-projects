# FastAPI Weather

A beginner-friendly FastAPI service for **locations**, **current conditions**, and **short forecasts** — all in memory with no external weather provider.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc). See `app/main.py` for the OpenAPI walkthrough.

## What you get

| Area | Behavior |
|------|----------|
| Locations | List, create, get, delete tracked cities |
| Current | Read and patch temperature, humidity, wind, condition |
| Forecast | Multi-day highs, lows, and precipitation chance |
| Search | `GET /locations?q=` matches city, region, or country code |
| Conflicts | Duplicate city + country → **409** |

## Seed data

| Id | City | Country | Current condition |
|----|------|---------|-------------------|
| `1` | San Francisco | US | Partly cloudy |
| `2` | London | GB | Overcast |
| `3` | Tokyo | JP | Clear |

## Setup

```bash
cd beginner/fastapi-weather
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

## Walkthrough (curl)

```bash
curl -s http://127.0.0.1:8000/api/v1/locations/1/current | jq .

curl -s http://127.0.0.1:8000/api/v1/locations/1/forecast | jq .

curl -s -X POST http://127.0.0.1:8000/api/v1/locations \
  -H "Content-Type: application/json" \
  -d '{"city":"Paris","country_code":"FR","region":"Île-de-France"}'

curl -s -X PATCH http://127.0.0.1:8000/api/v1/locations/4/current \
  -H "Content-Type: application/json" \
  -d '{"temp_c":15.5,"condition":"Light rain"}'
```

Use `/docs` → **weather** to explore endpoints interactively.

## Layout

```
app/
  main.py
  schemas/weather.py
  repositories/weather_repository.py
  services/weather_service.py
  api/v1/endpoints/locations.py
tests/api/v1/test_weather.py
```

## API reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Liveness |
| GET | `/api/v1/locations` | List (query: `q`) |
| POST | `/api/v1/locations` | Add location |
| GET | `/api/v1/locations/{id}` | Location metadata |
| DELETE | `/api/v1/locations/{id}` | Remove location |
| GET | `/api/v1/locations/{id}/current` | Current conditions |
| PATCH | `/api/v1/locations/{id}/current` | Update current readings |
| GET | `/api/v1/locations/{id}/forecast` | Forecast days |

## Tests and lint

```bash
pytest -v
ruff check app tests
```

## Docker

```bash
docker build -t fastapi-weather .
docker run --rm -p 8000:8000 fastapi-weather
```
