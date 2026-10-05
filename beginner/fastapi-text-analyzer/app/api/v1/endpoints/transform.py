from typing import Annotated

from fastapi import APIRouter, Body, Depends

from app.api.deps import get_text_service
from app.schemas.text import TransformRead, TransformRequest
from app.services.text_service import TextService

router = APIRouter()

_EXAMPLES = {
    "slug": {
        "summary": "URL slug",
        "description": "Lowercase, with punctuation turned into single hyphens.",
        "value": {"text": "Hello, World!", "mode": "slug"},
    },
    "title": {
        "summary": "Title case",
        "description": "Capitalize each ASCII word and leave punctuation in place.",
        "value": {"text": "don't stop", "mode": "title"},
    },
    "reverse": {
        "summary": "Reverse characters",
        "description": "Reverses the raw string, including spaces.",
        "value": {"text": "ab c", "mode": "reverse"},
    },
}


@router.post(
    "",
    response_model=TransformRead,
    summary="Transform text",
    response_description="Original text plus the transformed result",
    description=(
        "Applies one mode: `lower`, `upper`, `title`, `reverse`, or `slug`. "
        "`slug` can be an empty string when the text has no letters or digits. "
        "See GET /api/v1/options for the mode list."
    ),
    responses={
        422: {"description": "Text is blank or too long, or mode is not one of the five values."},
    },
)
def transform_text(
    payload: Annotated[TransformRequest, Body(openapi_examples=_EXAMPLES)],
    service: Annotated[TextService, Depends(get_text_service)],
) -> TransformRead:
    return service.transform(payload)
