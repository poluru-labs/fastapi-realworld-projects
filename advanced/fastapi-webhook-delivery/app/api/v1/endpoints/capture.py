"""Local subscriber sink for demos and tests (verify signatures here)."""

from typing import Any

from fastapi import APIRouter, Request

from app.core.webhook_signing import verify_signature

router = APIRouter(prefix="/dev", tags=["dev"])

CAPTURED: list[dict[str, Any]] = []


@router.post(
    "/capture",
    summary="Accept signed webhook POSTs (demo sink)",
    description=(
        "Point a webhook endpoint URL at this path during local development. "
        "The handler stores the last payloads in memory for inspection."
    ),
)
async def capture_webhook(request: Request) -> dict[str, str]:
    body = await request.body()
    timestamp = request.headers.get("X-Webhook-Timestamp", "")
    signature_header = request.headers.get("X-Webhook-Signature", "")
    signature_hex = signature_header.removeprefix("sha256=")

    record = {
        "body": body.decode("utf-8"),
        "headers": dict(request.headers),
        "timestamp": timestamp,
        "event": request.headers.get("X-Webhook-Event"),
        "webhook_id": request.headers.get("X-Webhook-Id"),
    }
    CAPTURED.append(record)
    if len(CAPTURED) > 50:
        del CAPTURED[0]

    secret = request.headers.get("X-Demo-Secret")
    if secret and signature_hex and timestamp:
        record["signature_valid"] = verify_signature(
            secret=secret,
            timestamp=timestamp,
            body=body,
            signature_hex=signature_hex,
        )

    return {"status": "accepted"}
