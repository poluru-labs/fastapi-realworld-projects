# FastAPI Unit Converter

A beginner-friendly FastAPI service for temperature, distance, and weight conversions, with a supported-unit lookup. Scale factors and formulas live in a static catalog (nothing is stored between requests).

Interactive documentation is served by the app itself: Swagger UI at `/docs` and ReDoc at `/redoc`. The OpenAPI description on the front page states the conversion rules, and **POST /api/v1/convert** includes ready-to-run examples (boiling point, aliases, inch to centimeter, kilogram to pound).

## What you get

| Feature | Details |
|---------|---------|
| Root welcome | `GET /` — short JSON pointer to `/docs` |
| Health | `GET /api/v1/health` — liveness for probes and monitoring |
| Unit lookup | `GET /api/v1/units` and `GET /api/v1/units/{category}` |
| Convert | `POST /api/v1/convert` — one value, two units, same category |
| Aliases | Case-insensitive codes (`C`, `km`, `lb`) resolve to canonical names |
| Validation | Finite numbers only; length and mass cannot be negative |
| Absolute zero | Temperatures colder than −273.15 °C are rejected |
| Errors | Domain errors return JSON `{"detail": "..."}` with an HTTP status |
| CORS | Configurable origins (defaults allow local frontends on port 3000) |
| Tests | Pytest coverage for lookup, classic conversions, and error cases |

## Project layout

```
app/
  main.py                 # App factory, OpenAPI text, CORS, exception handlers
  core/                   # Settings (pydantic-settings), AppError
  api/v1/endpoints/       # HTTP route handlers (health, units, convert)
  schemas/                # Pydantic request/response models
  repositories/           # Static unit catalog and exact scale factors
  services/               # Conversion rules
tests/
  api/v1/                 # API integration tests
```

### Request flow (end to end)

```mermaid
flowchart LR
  Client --> Router["API router /api/v1"]
  Router --> Endpoints["endpoints/convert.py"]
  Endpoints --> Service["ConversionService"]
  Service --> Repo["UnitRepository"]
  Repo --> Catalog["Static unit catalog"]
```

1. **HTTP** — FastAPI matches the path and parses the body into `ConversionRequest`.
2. **Dependencies** — `get_conversion_service` injects a shared `ConversionService` and the unit catalog.
3. **Service** — Resolves aliases, applies the category formula, and maps bad units to `AppError`.
4. **Repository** — Read-only list of categories, codes, symbols, and exact decimal factors.

## Setup

From this directory:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Optional environment file:

```bash
cp .env.example .env
```

See `.env.example` for `APP_NAME`, `DEBUG`, `API_V1_PREFIX`, and `CORS_ORIGINS`.

## Run the server

```bash
uvicorn app.main:app --reload
```

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8000 | API root |
| http://127.0.0.1:8000/docs | Swagger UI (try endpoints in the browser) |
| http://127.0.0.1:8000/redoc | ReDoc |
| http://127.0.0.1:8000/openapi.json | Raw OpenAPI schema |

If port 8000 is already in use, start with `--port 8001` and point the examples at that port.

## End-to-end walkthrough

With the server running, the following exercises lookup and conversion with `curl`. Responses are JSON.

**1. Welcome and health**

```bash
curl -s http://127.0.0.1:8000/
curl -s http://127.0.0.1:8000/api/v1/health
```

Expected health body: `{"status":"ok"}`.

**2. List every supported unit**

```bash
curl -s http://127.0.0.1:8000/api/v1/units
```

You should see three categories: `temperature`, `distance`, and `weight`. Each unit has a `code`, `symbol`, `aliases`, and `factor_to_base` (null for temperature).

**3. List one category**

```bash
curl -s http://127.0.0.1:8000/api/v1/units/distance
```

`base_unit` is `meter`. The inch factor is the string `"0.0254"` so the exact definition is preserved.

**4. Boiling point: 100 °C → °F**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/convert \
  -H "Content-Type: application/json" \
  -d '{"category": "temperature", "value": 100, "from_unit": "celsius", "to_unit": "fahrenheit"}'
```

```json
{
  "category": "temperature",
  "from_unit": "celsius",
  "to_unit": "fahrenheit",
  "from_symbol": "°C",
  "to_symbol": "°F",
  "input_value": 100.0,
  "result": 212.0,
  "formula": "°F = (°C × 9/5) + 32"
}
```

**5. Aliases are case-insensitive**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/convert \
  -H "Content-Type: application/json" \
  -d '{"category": "temperature", "value": 0, "from_unit": "c", "to_unit": "F"}'
```

`from_unit` in the response is the canonical code `celsius`, and `result` is `32.0`.

**6. Length and mass**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/convert \
  -H "Content-Type: application/json" \
  -d '{"category": "distance", "value": 1, "from_unit": "inch", "to_unit": "centimeter"}'
```

`result` is `2.54`.

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/convert \
  -H "Content-Type: application/json" \
  -d '{"category": "weight", "value": 1, "from_unit": "kg", "to_unit": "lb"}'
```

`result` is `2.204623` (half-up to 6 decimal places).

**7. Unknown unit**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/convert \
  -H "Content-Type: application/json" \
  -d '{"category": "distance", "value": 1, "from_unit": "stone", "to_unit": "meter"}'
```

Expect `400` and a `detail` string that lists the supported distance codes.

**8. Rejected values**

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST http://127.0.0.1:8000/api/v1/convert \
  -H "Content-Type: application/json" \
  -d '{"category": "distance", "value": -1, "from_unit": "meter", "to_unit": "foot"}'
```

Expect `422`. Length and mass must be ≥ 0. The same status is returned for a temperature below absolute zero (`-300` °C) and for an unknown category such as `volume`.

### Same flow in Swagger UI

Open http://127.0.0.1:8000/docs, expand **convert**, choose the **100 °C to °F** example, and execute. Expand **units** and run **GET /api/v1/units** to see the catalog the example codes come from.

### Automated end-to-end check

Tests hit the app via FastAPI’s `TestClient` (no running server needed):

```bash
pytest -v
```

This verifies the catalog, classic conversions (including −40 °C = −40 °F and 1 inch = 2.54 cm), aliases, absolute zero, and the OpenAPI document.

## API reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Welcome message |
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/units` | List categories and their units |
| GET | `/api/v1/units/{category}` | Units for `temperature`, `distance`, or `weight` |
| POST | `/api/v1/convert` | Convert `value` from `from_unit` to `to_unit` |

### Convert request

```json
{
  "category": "temperature | distance | weight",
  "value": 100,
  "from_unit": "celsius",
  "to_unit": "fahrenheit"
}
```

`category`, `from_unit`, and `to_unit` are trimmed and lowercased before lookup. `value` must be a finite JSON number (`NaN` and `Infinity` are rejected).

### Convert response

| Field | Meaning |
|-------|---------|
| `from_unit`, `to_unit` | Canonical codes, even if the request used an alias |
| `from_symbol`, `to_symbol` | Display symbols such as `°C` and `km` |
| `input_value` | The submitted number |
| `result` | Converted number. Identical units return the input unchanged. Otherwise the value is rounded half-up to 6 decimal places. |
| `formula` | The rule applied to this pair |

### Error catalog

| Situation | Status | `detail` |
|-----------|--------|----------|
| Unknown unit code for that category | 400 | `Unknown distance unit 'stone'. Supported codes: ...` |
| Temperature below −273.15 °C | 422 | `Temperature is below absolute zero (-273.15 °C / 0 K)` |
| Unknown category, negative length or mass, missing fields, non-finite value | 422 | Pydantic validation list |

Units do not convert across categories. `celsius` sent with `"category": "distance"` is an unknown distance unit (`400`).

## Supported units

Factors are exact decimals. `factor_to_base` is how many base units equal one of that unit.

### Temperature

Pivot: Celsius. There is no single scale factor, because Fahrenheit and Kelvin need an offset.

| Code | Symbol | Aliases | Notes |
|------|--------|---------|--------|
| `celsius` | °C | `c`, `degc` | Pivot unit |
| `fahrenheit` | °F | `f`, `degf` | |
| `kelvin` | K | `k` | 0 K is absolute zero |

| From | To | Result |
|------|----|--------|
| 0 °C | °F | 32 |
| 100 °C | °F | 212 |
| −40 °C | °F | −40 |
| 0 °C | K | 273.15 |
| −273.15 °C | °F | −459.67 |

### Distance

Pivot: meter. Inch, foot, yard, and mile use the international yard of 1959 (1 inch = 25.4 mm exactly).

| Code | Symbol | Aliases | Factor to meter |
|------|--------|---------|-----------------|
| `millimeter` | mm | `mm` | 0.001 |
| `centimeter` | cm | `cm` | 0.01 |
| `meter` | m | `m` | 1 |
| `kilometer` | km | `km` | 1000 |
| `inch` | in | `in` | 0.0254 |
| `foot` | ft | `ft` | 0.3048 |
| `yard` | yd | `yd` | 0.9144 |
| `mile` | mi | `mi` | 1609.344 |

| From | To | Result |
|------|----|--------|
| 1 inch | centimeter | 2.54 |
| 1 foot | inch | 12 |
| 1 mile | kilometer | 1.609344 |

### Weight

Pivot: gram. Ounce and pound use the international avoirdupois pound (exactly 0.45359237 kg).

| Code | Symbol | Aliases | Factor to gram |
|------|--------|---------|----------------|
| `milligram` | mg | `mg` | 0.001 |
| `gram` | g | `g` | 1 |
| `kilogram` | kg | `kg` | 1000 |
| `ounce` | oz | `oz` | 28.349523125 |
| `pound` | lb | `lb` | 453.59237 |

| From | To | Result |
|------|----|--------|
| 1000 g | kilogram | 1 |
| 1 kg | pound | 2.204623 |
| 1 pound | gram | 453.59237 |

## How conversion works

**Temperature** is converted through Celsius, then checked against absolute zero:

- °F = (°C × 9/5) + 32
- °C = (°F − 32) × 5/9
- K = °C + 273.15
- °C = K − 273.15

**Distance and weight** are linear. To convert a value:

```text
result = value × (factor of from_unit) / (factor of to_unit)
```

Example: 1 inch → centimeters is `1 × 0.0254 / 0.01 = 2.54`.

The same canonical unit on both sides skips the formula and returns the input unchanged, so alias pairs such as `mm` → `millimeter` do not get rounded.

## Lint

```bash
ruff check app tests
```

## Docker

Build and run the same API in a container:

```bash
docker build -t fastapi-unit-converter .
docker run --rm -p 8000:8000 fastapi-unit-converter
```

Then use the [end-to-end walkthrough](#end-to-end-walkthrough) against `http://127.0.0.1:8000`.
