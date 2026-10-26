from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi.responses import RedirectResponse

from app.api.deps import get_link_service
from app.schemas.link import CODE_PATTERN
from app.services.link_service import LinkService

router = APIRouter()

ShortCode = Annotated[
    str,
    Path(pattern=CODE_PATTERN.pattern, min_length=3, max_length=32),
]


@router.get(
    "/{code}",
    summary="Redirect to target URL",
    description=(
        "Returns **302** to the stored URL and increments `click_count`. "
        "Inactive links return **410 Gone**."
    ),
    responses={
        302: {"description": "Redirect to target URL."},
        410: {"description": "Link deactivated."},
    },
)
def redirect_to_target(
    code: ShortCode,
    service: Annotated[LinkService, Depends(get_link_service)],
) -> RedirectResponse:
    target = service.resolve_redirect(code)
    return RedirectResponse(url=target, status_code=302)
