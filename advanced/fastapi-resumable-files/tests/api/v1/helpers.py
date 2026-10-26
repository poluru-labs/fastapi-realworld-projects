from app.db.seed import SEED_UPLOAD_TOKEN

ADMIN_HEADERS = {"X-Admin-Key": "test-admin-key"}


def upload_headers(*, part_index: int, idempotency_key: str) -> dict[str, str]:
    return {
        "X-Upload-Token": SEED_UPLOAD_TOKEN,
        "X-Part-Index": str(part_index),
        "Idempotency-Key": idempotency_key,
    }
