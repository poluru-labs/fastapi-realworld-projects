TRACKER_TOKEN = "seed-token-delivery-van-01"
ADMIN_HEADERS = {"X-Admin-Key": "test-admin-key"}


def tracker_headers(*, idempotency_key: str) -> dict[str, str]:
    return {
        "X-Tracker-Token": TRACKER_TOKEN,
        "Idempotency-Key": idempotency_key,
    }
