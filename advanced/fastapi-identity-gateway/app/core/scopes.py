from app.core.exceptions import ForbiddenError


def parse_scope_string(raw: str) -> list[str]:
    return [part for part in raw.strip().split() if part]


def validate_requested_scopes(requested: list[str], allowed: list[str]) -> list[str]:
    allowed_set = set(allowed)
    invalid = [scope for scope in requested if scope not in allowed_set]
    if invalid:
        raise ForbiddenError(f"Scopes not allowed for client: {', '.join(invalid)}")
    if not requested:
        return list(allowed_set)[:1] if allowed else []
    return requested
