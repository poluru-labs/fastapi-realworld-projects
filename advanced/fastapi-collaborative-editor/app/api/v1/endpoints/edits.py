from typing import Annotated

from fastapi import APIRouter, Body, Query, status

from app.api.deps import CurrentUser, EditServiceDep, IdempotencyKey
from app.schemas.editor import EditSubmit, RevisionRead

router = APIRouter(prefix="/documents/{slug}/edits", tags=["edits"])

_SUBMIT_EXAMPLES = {
    "append": {
        "summary": "Insert text at end",
        "value": {
            "base_revision": 1,
            "patch": {"start": 11, "delete": 0, "insert": " Edit together."},
        },
    }
}


@router.get(
    "",
    response_model=list[RevisionRead],
    summary="List revision log after a cursor",
    description="Use **after_revision** for incremental sync (0 loads from the beginning).",
)
async def list_edits(
    slug: str,
    service: EditServiceDep,
    user: CurrentUser,
    after_revision: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[RevisionRead]:
    return await service.list_revisions(
        user,
        slug,
        after_revision=after_revision,
        limit=limit,
    )


@router.post(
    "",
    response_model=RevisionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an edit (idempotent)",
    description=(
        "Requires **Idempotency-Key**. **base_revision** must match the current document "
        "revision or you receive **409**. On success the server applies the patch, bumps "
        "revision, and enqueues **sync outbox** rows for other members."
    ),
)
async def submit_edit(
    slug: str,
    service: EditServiceDep,
    user: CurrentUser,
    idempotency_key: IdempotencyKey,
    payload: Annotated[EditSubmit, Body(openapi_examples=_SUBMIT_EXAMPLES)],
) -> RevisionRead:
    return await service.submit(user, slug, payload, idempotency_key=idempotency_key)
