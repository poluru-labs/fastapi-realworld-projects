from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_post_service
from app.schemas.post import TagCount
from app.services.post_service import PostService

router = APIRouter()


@router.get(
    "",
    response_model=list[TagCount],
    summary="List tags on published posts",
    description=(
        "Public. Counts include published posts only, so a tag that exists only on a "
        "draft is absent until that draft is published. Names are sorted alphabetically."
    ),
)
def list_tags(
    service: Annotated[PostService, Depends(get_post_service)],
) -> list[TagCount]:
    return service.list_tags()
