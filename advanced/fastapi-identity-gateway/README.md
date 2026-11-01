# Identity gateway API

Advanced FastAPI sample for **OAuth2/OIDC-shaped** identity: admin-registered clients,
**authorization_code** + **client_credentials** grants, JWT access tokens, **userinfo**, and
**introspection**. See `app/main.py` for the full OpenAPI narrative.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
python -m scripts.seed_data
uvicorn app.main:app --reload
```

## Seed (local demos)

| | |
|--|--|
| User | `demo@example.com` / `DemoPass123!` |
| Client ID | `cli_seed_dashboard` |
| Client secret | `cs_seed_secret_for_tests_only_32chars` |
| Redirect URI | `http://127.0.0.1:3000/callback` |

## Authorization code flow

1. `POST /api/v1/auth/login` → user bearer token.
2. `POST /api/v1/oauth/authorize` with client id, redirect URI, scopes → **code**.
3. `POST /api/v1/oauth/token` (`application/x-www-form-urlencoded`) with `grant_type=authorization_code`.
4. `GET /api/v1/oauth/userinfo` with OAuth access token.

## Machine flow

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/oauth/token \
  -d grant_type=client_credentials \
  -d client_id=cli_seed_dashboard \
  -d client_secret=cs_seed_secret_for_tests_only_32chars \
  -d scope=api:read
```

## Tests

```bash
pytest -v
ruff check app tests
```
