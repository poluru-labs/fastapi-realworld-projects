import hashlib
import secrets


def hash_webhook_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_webhook_token(token: str, token_hash: str) -> bool:
    return secrets.compare_digest(hash_webhook_token(token), token_hash)


def generate_webhook_token() -> str:
    return secrets.token_urlsafe(32)
