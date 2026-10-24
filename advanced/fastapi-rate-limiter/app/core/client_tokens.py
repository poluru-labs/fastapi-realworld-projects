import hashlib
import secrets


def hash_client_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def verify_client_key(key: str, key_hash: str) -> bool:
    return secrets.compare_digest(hash_client_key(key), key_hash)


def generate_client_key() -> str:
    return secrets.token_urlsafe(32)
