import hashlib
import hmac


def sign_payload(*, secret: str, timestamp: str, body: bytes) -> str:
    """HMAC-SHA256 over ``{timestamp}.{body}`` (Stripe-style webhook signing)."""
    message = timestamp.encode("utf-8") + b"." + body
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_signature(*, secret: str, timestamp: str, body: bytes, signature_hex: str) -> bool:
    expected = sign_payload(secret=secret, timestamp=timestamp, body=body)
    return hmac.compare_digest(expected, signature_hex)
