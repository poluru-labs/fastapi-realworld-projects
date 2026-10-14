from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_current_user, get_menu_service, get_optional_user
from app.schemas.menu import MenuItemCreate, MenuItemRead, MenuItemStatus, MenuItemUpdate
from app.schemas.user import UserRead
from app.services.menu_service import MenuService

router = APIRouter()

_CREATE_EXAMPLES = {
    "main": {
        "summary": "Draft menu item",
        "value": {
            "name": "Veggie Bowl",
            "description": "Roasted vegetables and grains.",
            "price_cents": 1199,
            "category": "Mains",
        },
    }
}


@router.get(
    "/categories",
    response_model=list[str],
    summary="List menu categories",
    description="Public callers see categories for active, available items only.",
)
def list_categories(
    service: Annotated[MenuService, Depends(get_menu_service)],
    actor: Annotated[UserRead | None, Depends(get_optional_user)],
) -> list[str]:
    return service.list_categories(actor)


@router.get(
    "",
    response_model=list[MenuItemRead],
    summary="List menu items",
    description=(
        "Anonymous callers see **active** and **available** items. "
        "Kitchen admins may filter drafts or sold-out rows with `status` and `available`."
    ),
)
def list_menu(
    service: Annotated[MenuService, Depends(get_menu_service)],
    actor: Annotated[UserRead | None, Depends(get_optional_user)],
    item_status: Annotated[
        MenuItemStatus | None,
        Query(alias="status", description="Admin-only filter."),
    ] = None,
    category: Annotated[str | None, Query()] = None,
    query: Annotated[str | None, Query()] = None,
    available: Annotated[bool | None, Query()] = None,
) -> list[MenuItemRead]:
    return service.list_menu(
        actor,
        status=item_status,
        category=category,
        query=query,
        available=available,
    )


@router.get("/{slug}", response_model=MenuItemRead, summary="Get one menu item")
def get_menu_item(
    slug: str,
    service: Annotated[MenuService, Depends(get_menu_service)],
    actor: Annotated[UserRead | None, Depends(get_optional_user)],
) -> MenuItemRead:
    return service.get_menu_item(actor, slug)


@router.post(
    "",
    response_model=MenuItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft menu item (admin)",
)
def create_menu_item(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MenuService, Depends(get_menu_service)],
    payload: Annotated[MenuItemCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
) -> MenuItemRead:
    return service.create_item(actor, payload)


@router.patch("/{slug}", response_model=MenuItemRead, summary="Update draft item (admin)")
def update_menu_item(
    slug: str,
    payload: MenuItemUpdate,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MenuService, Depends(get_menu_service)],
) -> MenuItemRead:
    return service.update_item(actor, slug, payload)


@router.post("/{slug}/activate", response_model=MenuItemRead, summary="Activate item (admin)")
def activate_menu_item(
    slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MenuService, Depends(get_menu_service)],
) -> MenuItemRead:
    return service.transition(actor, slug, MenuItemStatus.ACTIVE)


@router.post("/{slug}/deactivate", response_model=MenuItemRead, summary="Return item to draft")
def deactivate_menu_item(
    slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MenuService, Depends(get_menu_service)],
) -> MenuItemRead:
    return service.transition(actor, slug, MenuItemStatus.DRAFT)


@router.post("/{slug}/archive", response_model=MenuItemRead, summary="Archive item (admin)")
def archive_menu_item(
    slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MenuService, Depends(get_menu_service)],
) -> MenuItemRead:
    return service.transition(actor, slug, MenuItemStatus.ARCHIVED)


@router.post(
    "/{slug}/sold-out",
    response_model=MenuItemRead,
    summary="Mark active item sold out (admin)",
)
def mark_sold_out(
    slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MenuService, Depends(get_menu_service)],
) -> MenuItemRead:
    return service.set_available(actor, slug, False)


@router.post(
    "/{slug}/restock",
    response_model=MenuItemRead,
    summary="Mark active item available again (admin)",
)
def restock(
    slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MenuService, Depends(get_menu_service)],
) -> MenuItemRead:
    return service.set_available(actor, slug, True)
