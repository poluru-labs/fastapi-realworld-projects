from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, status

from app.api.deps import get_comment_service, get_current_user, get_optional_user
from app.schemas.comment import CommentCreate, CommentPage, CommentRead
from app.schemas.post import SLUG_PATTERN
from app.schemas.user import UserRead
from app.services.comment_service import CommentService

router = APIRouter()

Slug = Annotated[
    str,
    Path(
        pattern=SLUG_PATTERN.pattern,
        min_length=1,
        max_length=80,
        description="Slug of the post these comments belong to.",
        examples=["writing-apis-that-teach"],
    ),
]

_OPTIONAL_BEARER = {"security": [{}, {"OAuth2PasswordBearer": []}]}

_CREATE_EXAMPLES = {
    "note": {
        "summary": "A short comment",
        "value": {"body": "The 404 on a draft is the interesting part."},
    }
}


@router.get(
    "",
    response_model=CommentPage,
    summary="List comments on a post",
    description=(
        "Same visibility as the post: public when the post is published, author or admin "
        "when it is a draft or archived. Oldest comment first."
    ),
    responses={404: {"description": "No post with this slug, or it is hidden from you."}},
    openapi_extra=_OPTIONAL_BEARER,
)
def list_comments(
    slug: Slug,
    actor: Annotated[UserRead | None, Depends(get_optional_user)],
    service: Annotated[CommentService, Depends(get_comment_service)],
    limit: Annotated[int, Query(ge=1, le=100, description="Page size.")] = 20,
    offset: Annotated[int, Query(ge=0, description="How many comments to skip.")] = 0,
) -> CommentPage:
    return service.list_comments(actor, slug, limit=limit, offset=offset)


@router.post(
    "",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Comment on a published post",
    description=(
        "Any signed-in user, and only when the post is `published`. "
        "A draft you wrote still returns 409. A draft you cannot see returns 404."
    ),
    responses={
        404: {"description": "No post with this slug, or it is hidden from you."},
        409: {"description": "The post is visible to you but is not published."},
    },
)
def create_comment(
    slug: Slug,
    payload: Annotated[CommentCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[CommentService, Depends(get_comment_service)],
) -> CommentRead:
    return service.create_comment(actor, slug, payload)


@router.delete(
    "/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a comment",
    description="The comment author, the post author, or a platform admin.",
    responses={
        403: {"description": "You can see the post, but this comment is not yours to delete."},
        404: {"description": "The post is hidden, or this comment is not on this post."},
    },
)
def delete_comment(
    slug: Slug,
    comment_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[CommentService, Depends(get_comment_service)],
) -> None:
    service.delete_comment(actor, slug, comment_id)
