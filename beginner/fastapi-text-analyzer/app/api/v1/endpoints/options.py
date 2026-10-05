from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_text_service
from app.schemas.text import AnalyzerOptionsRead
from app.services.text_service import TextService

router = APIRouter()


@router.get(
    "",
    response_model=AnalyzerOptionsRead,
    summary="List analyzer options",
    description=(
        "Returns the reading-speed constant, request limits, transform modes, "
        "and the stop-word catalog used when ignore_stop_words is true."
    ),
)
def list_options(
    service: Annotated[TextService, Depends(get_text_service)],
) -> AnalyzerOptionsRead:
    return service.list_options()
