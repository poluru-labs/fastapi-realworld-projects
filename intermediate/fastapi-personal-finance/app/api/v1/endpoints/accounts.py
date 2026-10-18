from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, status

from app.api.deps import get_account_service, get_current_user
from app.schemas.finance import (
    SLUG_PATTERN,
    AccountCreate,
    AccountPage,
    AccountRead,
    AccountUpdate,
)
from app.schemas.user import UserRead
from app.services.account_service import AccountService

router = APIRouter()

Slug = Annotated[
    str,
    Path(
        pattern=SLUG_PATTERN.pattern,
        min_length=1,
        max_length=80,
        examples=["checking-main"],
    ),
]

_CREATE_EXAMPLES = {
    "checking": {
        "summary": "Everyday checking account",
        "value": {
            "name": "Household checking",
            "account_type": "checking",
            "currency": "USD",
            "opening_balance": 250.0,
        },
    }
}


@router.get(
    "",
    response_model=AccountPage,
    summary="List all accounts (admin)",
    description="Requires admin. Excludes archived accounts unless `include_archived=true`.",
)
def list_all_accounts(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AccountService, Depends(get_account_service)],
    include_archived: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AccountPage:
    return service.list_all_admin(
        actor,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )


@router.get("/mine", response_model=AccountPage, summary="List your accounts")
def list_my_accounts(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AccountService, Depends(get_account_service)],
    include_archived: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AccountPage:
    return service.list_mine(
        actor,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=AccountRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
)
def create_account(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AccountService, Depends(get_account_service)],
    payload: Annotated[AccountCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
) -> AccountRead:
    return service.create_account(actor, payload)


@router.get("/{slug}", response_model=AccountRead, summary="Get account by slug")
def get_account(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AccountService, Depends(get_account_service)],
) -> AccountRead:
    return service.get_account(actor, slug)


@router.patch("/{slug}", response_model=AccountRead, summary="Update account metadata")
def update_account(
    slug: Slug,
    payload: AccountUpdate,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AccountService, Depends(get_account_service)],
) -> AccountRead:
    return service.update_account(actor, slug, payload)


@router.post("/{slug}/archive", response_model=AccountRead, summary="Archive account")
def archive_account(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AccountService, Depends(get_account_service)],
) -> AccountRead:
    return service.archive(actor, slug)


@router.post("/{slug}/restore", response_model=AccountRead, summary="Restore archived account")
def restore_account(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AccountService, Depends(get_account_service)],
) -> AccountRead:
    return service.restore(actor, slug)
