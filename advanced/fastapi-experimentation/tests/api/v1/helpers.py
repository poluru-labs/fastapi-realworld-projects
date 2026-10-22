ADMIN_HEADERS = {"X-Admin-Key": "test-admin-key"}
CHECKOUT_TOKEN = "seed-token-checkout-button"


def experiment_headers(*, idempotency_key: str) -> dict[str, str]:
    return {
        "X-Experiment-Token": CHECKOUT_TOKEN,
        "Idempotency-Key": idempotency_key,
    }
