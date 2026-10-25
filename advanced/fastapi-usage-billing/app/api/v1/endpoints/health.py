import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.deps import DbSession
from app.schemas.health import HealthLive, HealthReady

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/health/live",
    response_model=HealthLive,
    summary="Liveness",
    description=(
        "Process is up. Does not check the database. Use this for a container liveness probe."
    ),
)
def live() -> HealthLive:
    return HealthLive(status="ok")


@router.get(
    "/health/ready",
    response_model=HealthReady,
    summary="Readiness",
    description=(
        "Database accepts a query. Returns 503 when it does not. Use this for a readiness probe."
    ),
    responses={503: {"model": HealthReady, "description": "Database is unreachable."}},
)
async def ready(session: DbSession) -> JSONResponse:
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Readiness check failed")
        body = HealthReady(status="unavailable", database="error")
        return JSONResponse(status_code=503, content=body.model_dump())
    body = HealthReady(status="ok", database="ok")
    return JSONResponse(status_code=200, content=body.model_dump())
