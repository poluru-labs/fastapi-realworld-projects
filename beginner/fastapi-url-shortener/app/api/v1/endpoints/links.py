from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.deps import get_link_service
from app.schemas.link import CODE_PATTERN, LinkCreate, LinkRead, LinkUpdate
from app.services.link_service import LinkService

router = APIRouter()


@router.get(
    "",
    response_model=list[LinkRead],
    summary="List short links",
    description=(
        "Sorted by newest first. Filter with `is_active` or search `q` in code, title, or URL."
    ),
)
def list_links(
    service: Annotated[LinkService, Depends(get_link_service)],
    is_active: Annotated[bool | None, Query(description="true or false")] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> list[LinkRead]:
    return service.list_links(is_active=is_active, q=q)


@router.post(
    "",
    response_model=LinkRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a short link",
    responses={409: {"description": "Custom code already taken."}},
)
def create_link(
    payload: LinkCreate,
    service: Annotated[LinkService, Depends(get_link_service)],
) -> LinkRead:
    return service.create_link(payload)


ShortCode = Annotated[
    str,
    Path(pattern=CODE_PATTERN.pattern, min_length=3, max_length=32),
]


@router.get(
    "/{code}",
    response_model=LinkRead,
    summary="Get link metadata",
)
def get_link(
    code: ShortCode,
    service: Annotated[LinkService, Depends(get_link_service)],
) -> LinkRead:
    return service.get_link(code)


@router.patch(
    "/{code}",
    response_model=LinkRead,
    summary="Update a link",
)
def update_link(
    code: ShortCode,
    payload: LinkUpdate,
    service: Annotated[LinkService, Depends(get_link_service)],
) -> LinkRead:
    return service.update_link(code, payload)


@router.delete(
    "/{code}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a short link",
)
def delete_link(
    code: ShortCode,
    service: Annotated[LinkService, Depends(get_link_service)],
) -> None:
    service.delete_link(code)
