from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_post_service
from app.schemas.post import PostPage
from app.schemas.user import UserRead
from app.services.post_service import PostService

router = APIRouter()


@router.get(
    "",
    response_model=PostPage,
    summary="Home feed",
    description=(
        "Signed-in timeline: published posts from you and accounts you follow. "
        "Includes public and followers-only posts when the visibility rule allows. "
        "Newest `published_at` first. Drafts never appear here."
    ),
)
def home_feed(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[PostService, Depends(get_post_service)],
    limit: Annotated[int, Query(ge=1, le=100, description="Page size.")] = 20,
    offset: Annotated[int, Query(ge=0, description="How many matching posts to skip.")] = 0,
) -> PostPage:
    return service.list_home_feed(actor, limit=limit, offset=offset)
