from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, status

from app.api.deps import get_current_user, get_optional_user, get_post_service
from app.schemas.post import SLUG_PATTERN, PostCreate, PostPage, PostRead, PostStatus, PostUpdate
from app.schemas.user import UserRead
from app.services.post_service import PostService

router = APIRouter()

Slug = Annotated[
    str,
    Path(
        pattern=SLUG_PATTERN.pattern,
        min_length=1,
        max_length=80,
        description="Lowercase words separated by hyphens.",
        examples=["writing-apis-that-teach"],
    ),
]

# Swagger treats a dependency bearer as required. This OR lets callers try the route
# with no token, which is how anonymous readers load a published post.
_OPTIONAL_BEARER = {"security": [{}, {"OAuth2PasswordBearer": []}]}

_CREATE_EXAMPLES = {
    "from_title": {
        "summary": "Draft, slug taken from the title",
        "description": "The post stays a draft until POST .../publish.",
        "value": {
            "title": "Pagination without leaking drafts",
            "summary": "The public list and your drafts are different queries.",
            "body": "The public list only returns published posts.",
            "tags": ["fastapi", "pagination"],
        },
    },
    "custom_slug": {
        "summary": "Draft with an explicit slug",
        "description": "Use this when the title would slugify to a slug that is already taken.",
        "value": {
            "title": "Pagination without leaking drafts",
            "summary": "A second take on the same title.",
            "body": "Same title, different slug.",
            "tags": ["fastapi"],
            "slug": "pagination-second-take",
        },
    },
}


@router.get(
    "",
    response_model=PostPage,
    summary="List published posts",
    description=(
        "Public. Drafts and archived posts are never included, even if you pass a token "
        "or `status`. Filters combine with AND. `q` matches title, summary, and body, "
        "ignoring case. `tag` ignores case. Newest `published_at` comes first."
    ),
)
def list_posts(
    service: Annotated[PostService, Depends(get_post_service)],
    tag: Annotated[
        str | None,
        Query(max_length=32, description="Keep posts that include this tag.", examples=["fastapi"]),
    ] = None,
    author_id: Annotated[
        int | None,
        Query(ge=1, description="Keep posts written by this user id."),
    ] = None,
    q: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=80,
            description="Case-insensitive search across title, summary, and body.",
        ),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Page size.")] = 20,
    offset: Annotated[int, Query(ge=0, description="How many matching posts to skip.")] = 0,
) -> PostPage:
    return service.list_published(
        tag=tag,
        author_id=author_id,
        query=q,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/mine",
    response_model=PostPage,
    summary="List your posts",
    description=(
        "Every status you wrote, including drafts. A platform admin does not see other "
        "people's drafts here; open those by slug. Newest `updated_at` comes first."
    ),
)
def list_my_posts(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[PostService, Depends(get_post_service)],
    post_status: Annotated[
        PostStatus | None,
        Query(alias="status", description="Keep only your posts in this status."),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Page size.")] = 20,
    offset: Annotated[int, Query(ge=0, description="How many matching posts to skip.")] = 0,
) -> PostPage:
    return service.list_mine(actor, status=post_status, limit=limit, offset=offset)


@router.post(
    "",
    response_model=PostRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft",
    description=(
        "Any signed-in user. New posts are always `draft`. The slug comes from the title "
        "unless you send one. Slugs are unique and do not change later."
    ),
    responses={
        409: {"description": "Another post already uses this slug."},
        422: {"description": "Title, slug, or tags failed validation."},
    },
)
def create_post(
    payload: Annotated[PostCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostRead:
    return service.create_post(actor, payload)


@router.get(
    "/{slug}",
    response_model=PostRead,
    summary="Get one post",
    description=(
        "Published posts need no token. Send a valid access token to preview your own "
        "draft or archive, or any post if you are a platform admin. A missing token on "
        "a hidden post is 404. A bad token is 401, not an anonymous read."
    ),
    responses={
        404: {"description": "No post with this slug, or it is hidden from you."},
    },
    openapi_extra=_OPTIONAL_BEARER,
)
def get_post(
    slug: Slug,
    actor: Annotated[UserRead | None, Depends(get_optional_user)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostRead:
    return service.get_post(actor, slug)


@router.patch(
    "/{slug}",
    response_model=PostRead,
    summary="Edit your post",
    description=(
        "Author only. Platform admin can read and archive, but cannot rewrite the body. "
        "Send the fields that change. Tags, when sent, replace the whole list. "
        "The slug stays the same."
    ),
    responses={
        403: {"description": "You can see the post, but you are not the author."},
        404: {"description": "No post with this slug, or it is hidden from you."},
    },
)
def update_post(
    slug: Slug,
    payload: PostUpdate,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostRead:
    return service.update_post(actor, slug, payload)


@router.post(
    "/{slug}/publish",
    response_model=PostRead,
    summary="Publish a draft",
    description="Author only. Legal move: `draft` → `published`. Sets `published_at` to now.",
    responses={
        403: {"description": "Only the author can publish."},
        409: {"description": "The post is not a draft."},
    },
)
def publish_post(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostRead:
    return service.publish(actor, slug)


@router.post(
    "/{slug}/unpublish",
    response_model=PostRead,
    summary="Return a published post to draft",
    description=(
        "Author only. Legal move: `published` → `draft`. Clears `published_at`. "
        "The post leaves the public list. An archived post uses restore instead."
    ),
    responses={409: {"description": "The post is not published."}},
)
def unpublish_post(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostRead:
    return service.unpublish(actor, slug)


@router.post(
    "/{slug}/archive",
    response_model=PostRead,
    summary="Archive a published post",
    description=(
        "Author or platform admin. Legal move: `published` → `archived`. "
        "`published_at` stays, as a record of when it was live. "
        "A draft cannot skip straight to archived."
    ),
    responses={
        403: {"description": "You are not the author or an admin."},
        409: {"description": "The post is not published."},
    },
)
def archive_post(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostRead:
    return service.archive(actor, slug)


@router.post(
    "/{slug}/restore",
    response_model=PostRead,
    summary="Restore an archived post to draft",
    description=(
        "Author only. Legal move: `archived` → `draft`. Clears `published_at`. "
        "Publish again when it should return to the public list."
    ),
    responses={409: {"description": "The post is not archived."}},
)
def restore_post(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostRead:
    return service.restore(actor, slug)


@router.delete(
    "/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a post",
    description="Author or platform admin. Comments on the post are deleted with it.",
    responses={
        403: {"description": "You can see the post, but you cannot delete it."},
        404: {"description": "No post with this slug, or it is hidden from you."},
    },
)
def delete_post(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> None:
    service.delete_post(actor, slug)
