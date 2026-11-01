from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_flag_service, get_runtime_token
from app.schemas.evaluate import EvaluateRequest, EvaluateResponse
from app.services.flag_service import FlagService

router = APIRouter()


@router.post(
    "/evaluate",
    response_model=EvaluateResponse,
    summary="Evaluate flags for a user context",
    description=(
        "Server-side evaluation for apps and services. Requires `X-Runtime-Token` "
        "scoped to the flag owner. Returns per-flag `enabled` plus a human-readable `reason`."
    ),
    responses={
        404: {"description": "Unknown runtime token."},
    },
)
def evaluate_flags(
    payload: EvaluateRequest,
    runtime_token: Annotated[str, Depends(get_runtime_token)],
    service: Annotated[FlagService, Depends(get_flag_service)],
) -> EvaluateResponse:
    return service.evaluate(runtime_token=runtime_token, payload=payload)
