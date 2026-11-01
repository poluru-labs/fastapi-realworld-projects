from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_monitor_service
from app.schemas.monitor import StatusPageRead
from app.services.monitor_service import MonitorService

router = APIRouter()


@router.get(
    "/{slug}",
    response_model=StatusPageRead,
    summary="Public status page",
    description=(
        "No authentication. Only monitors with `is_public=true` are visible; "
        "others return **404**."
    ),
)
def read_status_page(
    slug: str,
    service: Annotated[MonitorService, Depends(get_monitor_service)],
) -> StatusPageRead:
    return service.public_status(slug)
