ADMIN_HEADERS = {"X-Admin-Key": "test-admin-key"}
RUNNER_HEADERS = {"X-Runner-Key": "test-runner-key"}


def runner_with_idempotency(key: str) -> dict[str, str]:
    return {**RUNNER_HEADERS, "Idempotency-Key": key}
