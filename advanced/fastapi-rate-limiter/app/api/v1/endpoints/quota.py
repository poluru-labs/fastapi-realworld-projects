from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from app.api.deps import DbSession, IdempotencyKey, RateLimitClientDep
from app.schemas.rate_limiting import QuotaRequest, QuotaStatus
from app.services.quota_service import QuotaService

router = APIRouter()


@router.post(
    "/check",
    response_model=QuotaStatus,
    summary="Check quota without consuming",
    description=(
        "Requires `X-Client-Id` (client slug) and `X-Client-Key` (secret). "
        "Returns whether `cost` fits in the current fixed window."
    ),
)
async def check_quota(
    client: RateLimitClientDep,
    session: DbSession,
    payload: QuotaRequest,
) -> QuotaStatus:
    return await QuotaService(session).check(client, payload)


@router.post(
    "/consume",
    summary="Consume quota",
    description=(
        "Increments the counter when allowed. Requires **Idempotency-Key**. "
        "Returns **429** with the same JSON body when the limit is exceeded."
    ),
    responses={
        200: {"model": QuotaStatus},
        429: {"model": QuotaStatus},
    },
)
async def consume_quota(
    client: RateLimitClientDep,
    session: DbSession,
    idempotency_key: IdempotencyKey,
    payload: QuotaRequest,
) -> Response:
    body, status_code = await QuotaService(session).consume(
        client,
        idempotency_key,
        payload,
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json"),
    )
