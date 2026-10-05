# Authentication Services API

Intermediate FastAPI project: registration, bcrypt password hashing, JWT access tokens, refresh-token rotation with server-side revocation, logout, and role-based access control (RBAC). Users and refresh tokens live in memory (reset on restart).

## Features

| Area | Behavior |
|------|----------|
| **Register** | `POST /api/v1/auth/register` — email, password (8+ chars), full name |
| **Login** | `POST /api/v1/auth/login` — OAuth2 password form (`username` = email) |
| **Refresh** | `POST /api/v1/auth/refresh` — new pair; old refresh JTI invalidated (rotation) |
| **Logout** | `POST /api/v1/auth/logout` — revokes refresh token |
| **Profile** | `GET /api/v1/auth/me` — Bearer access token |
| **Users** | Admin list; users may read own profile by id |
| **Seed admin** | `admin@example.com` / `AdminPass123!` |

## Project layout

```
app/
  core/           config, AppError types, JWT + bcrypt helpers
  api/deps.py     OAuth2 bearer, current user, role guards
  api/v1/endpoints/   auth, users, health
  repositories/   users + refresh token store
  services/       auth and user business logic
tests/
```

## Setup

```bash
cd intermediate/authentication-services
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # set SECRET_KEY for non-local use
```

## Run

```bash
uvicorn app.main:app --reload
```

- Docs: http://127.0.0.1:8000/docs  
- Health: http://127.0.0.1:8000/api/v1/health  

## End-to-end auth flow

**1. Register**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"SecurePass1!","full_name":"You"}'
```

**2. Login (form-urlencoded)**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -d "username=you@example.com&password=SecurePass1!"
```

Save `access_token` and `refresh_token` from the JSON response.

**3. Call a protected route**

```bash
curl -s http://127.0.0.1:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

**4. Refresh tokens**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh_token>"}'
```

**5. Logout**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/logout \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh_token>"}'
```

**Admin: list users**

```bash
curl -s http://127.0.0.1:8000/api/v1/users \
  -H "Authorization: Bearer <admin_access_token>"
```

## API reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/register` | — | Create account |
| POST | `/api/v1/auth/login` | — | Issue token pair |
| POST | `/api/v1/auth/refresh` | — | Rotate refresh token |
| POST | `/api/v1/auth/logout` | — | Revoke refresh token |
| GET | `/api/v1/auth/me` | Bearer | Current user |
| GET | `/api/v1/users` | Admin | List users |
| GET | `/api/v1/users/{id}` | Bearer | Own profile or admin |
| GET | `/api/v1/health` | — | Liveness |

## Test and lint

```bash
pytest -v
ruff check app tests
```

## Docker

```bash
docker build -t authentication-services .
docker run --rm -p 8000:8000 -e SECRET_KEY=your-production-secret authentication-services
```

## Production notes

Replace in-memory stores with a database and Redis (or similar) for refresh tokens. Use a strong `SECRET_KEY`, HTTPS only, and short access-token TTL. Consider rate limiting on `/login` and `/register`.
