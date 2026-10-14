"""Menu visibility and admin lifecycle live here."""

from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.menu_repository import MenuItemRecord, MenuRepository
from app.schemas.menu import MenuItemCreate, MenuItemRead, MenuItemStatus, MenuItemUpdate, slugify
from app.schemas.user import UserRead, UserRole

_TRANSITIONS: dict[MenuItemStatus, set[MenuItemStatus]] = {
    MenuItemStatus.DRAFT: {MenuItemStatus.ACTIVE, MenuItemStatus.ARCHIVED},
    MenuItemStatus.ACTIVE: {MenuItemStatus.DRAFT, MenuItemStatus.ARCHIVED},
    MenuItemStatus.ARCHIVED: {MenuItemStatus.DRAFT},
}


def can_view_menu_item(actor: UserRead | None, record: MenuItemRecord) -> bool:
    if record.status is MenuItemStatus.ACTIVE:
        return True
    if actor is None:
        return False
    return actor.role is UserRole.ADMIN


class MenuService:
    def __init__(self, *, menu: MenuRepository) -> None:
        self._menu = menu

    def list_menu(
        self,
        actor: UserRead | None,
        *,
        status: MenuItemStatus | None,
        category: str | None,
        query: str | None,
        available: bool | None,
    ) -> list[MenuItemRead]:
        rows = self._menu.list_all()
        if actor is None or actor.role is not UserRole.ADMIN:
            rows = [
                item
                for item in rows
                if item.status is MenuItemStatus.ACTIVE and item.available
            ]
        elif status is not None:
            rows = [item for item in rows if item.status is status]

        if category is not None:
            needle = category.strip().casefold()
            if needle:
                rows = [item for item in rows if item.category.casefold() == needle]
        if available is not None:
            rows = [item for item in rows if item.available is available]
        if query is not None:
            needle = query.strip().casefold()
            if needle:
                rows = [
                    item
                    for item in rows
                    if needle in item.name.casefold() or needle in item.description.casefold()
                ]
        rows.sort(key=lambda item: (item.category.casefold(), item.name.casefold(), item.id))
        return [self._to_read(item) for item in rows]

    def get_menu_item(self, actor: UserRead | None, slug: str) -> MenuItemRead:
        return self._to_read(self.visible_record(actor, slug))

    def visible_record(self, actor: UserRead | None, slug: str) -> MenuItemRecord:
        record = self._menu.get_by_slug(slug)
        if record is None or not can_view_menu_item(actor, record):
            raise NotFoundError("MenuItem", slug)
        if actor is None or actor.role is not UserRole.ADMIN:
            if not record.available:
                raise NotFoundError("MenuItem", slug)
        return record

    def orderable_record(self, slug: str) -> MenuItemRecord:
        record = self._menu.get_by_slug(slug)
        if (
            record is None
            or record.status is not MenuItemStatus.ACTIVE
            or not record.available
        ):
            raise NotFoundError("MenuItem", slug)
        return record

    def list_categories(self, actor: UserRead | None) -> list[str]:
        items = self.list_menu(actor, status=None, category=None, query=None, available=None)
        categories = {item.category for item in items}
        return sorted(categories, key=str.casefold)

    def create_item(self, actor: UserRead, payload: MenuItemCreate) -> MenuItemRead:
        self._require_admin(actor)
        slug = payload.slug or slugify(payload.name)
        if not slug:
            raise ConflictError("Could not derive a slug from the name")
        if self._menu.slug_taken(slug):
            raise ConflictError("Another menu item already uses this slug")
        now = datetime.now(UTC)
        record = MenuItemRecord(
            id=self._menu.allocate_id(),
            slug=slug,
            name=payload.name,
            description=payload.description,
            price_cents=payload.price_cents,
            category=payload.category,
            status=MenuItemStatus.DRAFT,
            available=payload.available,
            created_at=now,
            updated_at=now,
        )
        self._menu.add(record)
        return self._to_read(record)

    def update_item(self, actor: UserRead, slug: str, payload: MenuItemUpdate) -> MenuItemRead:
        self._require_admin(actor)
        record = self._require_item(slug)
        if record.status is not MenuItemStatus.DRAFT:
            raise ConflictError("Only draft menu items accept content edits")
        changes = payload.model_dump(exclude_unset=True)
        for field in ("name", "description", "price_cents", "category", "available"):
            if field in changes:
                setattr(record, field, changes[field])
        record.updated_at = datetime.now(UTC)
        self._menu.save(record)
        return self._to_read(record)

    def transition(self, actor: UserRead, slug: str, target: MenuItemStatus) -> MenuItemRead:
        self._require_admin(actor)
        record = self._require_item(slug)
        allowed = _TRANSITIONS.get(record.status, set())
        if target not in allowed:
            raise ConflictError(f"Cannot move from {record.status.value} to {target.value}")
        record.status = target
        record.updated_at = datetime.now(UTC)
        self._menu.save(record)
        return self._to_read(record)

    def set_available(self, actor: UserRead, slug: str, available: bool) -> MenuItemRead:
        self._require_admin(actor)
        record = self._require_item(slug)
        if record.status is not MenuItemStatus.ACTIVE:
            raise ConflictError("Only active menu items can be marked available or sold out")
        record.available = available
        record.updated_at = datetime.now(UTC)
        self._menu.save(record)
        return self._to_read(record)

    def _require_item(self, slug: str) -> MenuItemRecord:
        record = self._menu.get_by_slug(slug)
        if record is None:
            raise NotFoundError("MenuItem", slug)
        return record

    def _to_read(self, record: MenuItemRecord) -> MenuItemRead:
        return MenuItemRead(
            id=record.id,
            slug=record.slug,
            name=record.name,
            description=record.description,
            price_cents=record.price_cents,
            category=record.category,
            status=record.status,
            available=record.available,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _require_admin(actor: UserRead) -> None:
        if actor.role is not UserRole.ADMIN:
            raise ForbiddenError("Only a platform admin can manage the menu")
