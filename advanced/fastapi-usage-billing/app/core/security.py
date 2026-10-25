import hashlib
import secrets


def generate_api_key() -> str:
    return f"sk_live_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str, pepper: str) -> str:
    return hashlib.sha256(f"{pepper}:{api_key}".encode()).hexdigest()
