ADMIN_HEADERS = {"X-Admin-Key": "test-admin-key"}


def client_headers(*, idempotency_key: str | None = None) -> dict[str, str]:
    headers = {
        "X-Client-Id": "mobile-app",
        "X-Client-Key": "seed-client-mobile-app",
    }
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    return headers
