"""Plan visibility, catalog filters, and admin lifecycle live here."""

from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.plan_repository import PlanRecord, PlanRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.plan import (
    PlanCreate,
    PlanRead,
    PlanStatus,
    PlanUpdate,
    TagCount,
    slugify,
)
from app.schemas.user import UserRead, UserRole

_TRANSITIONS: dict[PlanStatus, set[PlanStatus]] = {
    PlanStatus.DRAFT: {PlanStatus.ACTIVE, PlanStatus.ARCHIVED},
    PlanStatus.ACTIVE: {PlanStatus.DRAFT, PlanStatus.ARCHIVED},
    PlanStatus.ARCHIVED: {PlanStatus.DRAFT},
}


def can_view_plan(actor: UserRead | None, record: PlanRecord) -> bool:
    if record.status is PlanStatus.ACTIVE:
        return True
    if actor is None:
        return False
    if actor.role is UserRole.ADMIN:
        return True
    return actor.id == record.owner_id


class PlanService:
    def __init__(
        self,
        *,
        plans: PlanRepository,
        subscriptions: SubscriptionRepository,
        users: UserRepository,
    ) -> None:
        self._plans = plans
        self._subscriptions = subscriptions
        self._users = users

    def list_plans(
        self,
        actor: UserRead | None,
        *,
        status: PlanStatus | None,
        tag: str | None,
        query: str | None,
        interval: str | None,
    ) -> list[PlanRead]:
        rows = self._plans.list_all()
        if actor is None or actor.role is not UserRole.ADMIN:
            rows = [plan for plan in rows if plan.status is PlanStatus.ACTIVE]
        elif status is not None:
            rows = [plan for plan in rows if plan.status is status]

        if tag is not None:
            needle = tag.strip().casefold()
            if needle:
                rows = [plan for plan in rows if needle in plan.tags]
        if query is not None:
            needle = query.strip().casefold()
            if needle:
                rows = [
                    plan
                    for plan in rows
                    if needle in plan.name.casefold() or needle in plan.summary.casefold()
                ]
        if interval is not None:
            needle = interval.strip().casefold()
            if needle:
                rows = [plan for plan in rows if plan.interval.value == needle]

        rows.sort(key=lambda plan: (plan.price_cents, plan.id))
        return [self._to_read(plan) for plan in rows]

    def get_plan(self, actor: UserRead | None, slug: str) -> PlanRead:
        return self._to_read(self.visible_record(actor, slug))

    def visible_record(self, actor: UserRead | None, slug: str) -> PlanRecord:
        record = self._plans.get_by_slug(slug)
        if record is None or not can_view_plan(actor, record):
            raise NotFoundError("Plan", slug)
        return record

    def create_plan(self, actor: UserRead, payload: PlanCreate) -> PlanRead:
        self._require_admin(actor, "Only a platform admin can create plans")
        slug = payload.slug or slugify(payload.name)
        if not slug:
            raise ConflictError("Could not derive a slug from the name")
        if self._plans.slug_taken(slug):
            raise ConflictError("Another plan already uses this slug")
        now = datetime.now(UTC)
        record = PlanRecord(
            id=self._plans.allocate_id(),
            slug=slug,
            name=payload.name,
            summary=payload.summary,
            description=payload.description,
            price_cents=payload.price_cents,
            interval=payload.interval,
            status=PlanStatus.DRAFT,
            owner_id=actor.id,
            tags=payload.tags,
            created_at=now,
            updated_at=now,
            activated_at=None,
        )
        self._plans.add(record)
        return self._to_read(record)

    def update_plan(self, actor: UserRead, slug: str, payload: PlanUpdate) -> PlanRead:
        self._require_admin(actor, "Only a platform admin can update plans")
        record = self._require_plan(slug)
        if record.status is not PlanStatus.DRAFT:
            raise ConflictError("Only draft plans accept content edits")
        changes = payload.model_dump(exclude_unset=True)
        for field in ("name", "summary", "description", "price_cents", "interval", "tags"):
            if field in changes:
                setattr(record, field, changes[field])
        record.updated_at = datetime.now(UTC)
        self._plans.save(record)
        return self._to_read(record)

    def transition(self, actor: UserRead, slug: str, target: PlanStatus) -> PlanRead:
        self._require_admin(actor, "Only a platform admin can change plan status")
        record = self._require_plan(slug)
        allowed = _TRANSITIONS.get(record.status, set())
        if target not in allowed:
            raise ConflictError(f"Cannot move from {record.status.value} to {target.value}")
        if target is PlanStatus.DRAFT and self._subscriptions.count_active_for_plan(record.id):
            raise ConflictError("Deactivate blocked while active subscriptions exist")
        now = datetime.now(UTC)
        record.status = target
        record.updated_at = now
        if target is PlanStatus.ACTIVE:
            record.activated_at = now
        if target is PlanStatus.DRAFT:
            record.activated_at = None
        self._plans.save(record)
        return self._to_read(record)

    def list_tags(self) -> list[TagCount]:
        counts: dict[str, int] = {}
        for plan in self._plans.list_all():
            if plan.status is not PlanStatus.ACTIVE:
                continue
            for tag in plan.tags:
                counts[tag] = counts.get(tag, 0) + 1
        return [TagCount(name=name, count=count) for name, count in sorted(counts.items())]

    def _require_plan(self, slug: str) -> PlanRecord:
        record = self._plans.get_by_slug(slug)
        if record is None:
            raise NotFoundError("Plan", slug)
        return record

    def _to_read(self, record: PlanRecord) -> PlanRead:
        owner = self._users.get_by_id(record.owner_id)
        owner_name = owner.full_name if owner else "Unknown"
        active = self._subscriptions.count_active_for_plan(record.id)
        return PlanRead(
            id=record.id,
            slug=record.slug,
            name=record.name,
            summary=record.summary,
            description=record.description,
            price_cents=record.price_cents,
            interval=record.interval,
            status=record.status,
            owner_id=record.owner_id,
            owner_name=owner_name,
            tags=record.tags,
            active_subscriber_count=active,
            created_at=record.created_at,
            updated_at=record.updated_at,
            activated_at=record.activated_at,
        )

    @staticmethod
    def _require_admin(actor: UserRead, message: str) -> None:
        if actor.role is not UserRole.ADMIN:
            raise ForbiddenError(message)
