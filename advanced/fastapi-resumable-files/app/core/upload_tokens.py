import hashlib
import secrets


def hash_upload_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_upload_token(token: str, token_hash: str) -> bool:
    return secrets.compare_digest(hash_upload_token(token), token_hash)


def generate_upload_token() -> str:
    return secrets.token_urlsafe(32)
