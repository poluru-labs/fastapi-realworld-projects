
INGEST_HEADERS = {
    "X-Ingest-Key": "test-ingest-key",
}
ADMIN_HEADERS = {
    "X-Admin-Key": "test-admin-key",
}


def ingest_headers(*, idempotency_key: str) -> dict[str, str]:
    return {
        **INGEST_HEADERS,
        "Idempotency-Key": idempotency_key,
    }
