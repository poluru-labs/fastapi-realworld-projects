DEVICE_TOKEN = "seed-token-warehouse-temp-01"
ADMIN_HEADERS = {"X-Admin-Key": "test-admin-key"}


def device_headers(*, idempotency_key: str) -> dict[str, str]:
    return {
        "X-Device-Token": DEVICE_TOKEN,
        "Idempotency-Key": idempotency_key,
    }
