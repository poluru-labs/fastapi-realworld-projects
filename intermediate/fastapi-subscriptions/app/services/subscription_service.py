"""Subscribe, billing periods, cancel rules, and privacy live here."""

from datetime import UTC, datetime, timedelta

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.plan_repository import PlanRepository
from app.repositories.subscription_repository import SubscriptionRecord, SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.plan import BillingInterval, PlanStatus
from app.schemas.subscription import SubscriptionCreate, SubscriptionRead, SubscriptionStatus
from app.schemas.user import UserRead, UserRole
from app.services.plan_service import can_view_plan


def _period_end(start: datetime, interval: BillingInterval) -> datetime:
    days = 30 if interval is BillingInterval.MONTHLY else 365
    return start + timedelta(days=days)


class SubscriptionService:
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

    def list_subscriptions(
        self,
        actor: UserRead,
        *,
        plan_id: int | None,
        status: SubscriptionStatus | None,
    ) -> list[SubscriptionRead]:
        if actor.role is UserRole.ADMIN:
            rows = self._subscriptions.list_all()
        else:
            rows = self._subscriptions.list_for_user(actor.id)
        if plan_id is not None:
            rows = [row for row in rows if row.plan_id == plan_id]
        if status is not None:
            rows = [row for row in rows if row.status is status]
        rows.sort(key=lambda row: (row.created_at, row.id))
        return [self._to_read(row) for row in rows]

    def list_for_plan_slug(self, actor: UserRead, slug: str) -> list[SubscriptionRead]:
        if actor.role is not UserRole.ADMIN:
            raise ForbiddenError("Only a platform admin can list subscribers for a plan")
        plan = self._plans.get_by_slug(slug)
        if plan is None:
            raise NotFoundError("Plan", slug)
        return self.list_subscriptions(actor, plan_id=plan.id, status=None)

    def get_subscription(self, actor: UserRead, subscription_id: int) -> SubscriptionRead:
        row = self._subscriptions.get(subscription_id)
        if row is None or not self._can_view(actor, row):
            raise NotFoundError("Subscription", subscription_id)
        return self._to_read(row)

    def subscribe(self, actor: UserRead, payload: SubscriptionCreate) -> SubscriptionRead:
        plan = self._plans.get_by_slug(payload.plan_slug)
        if plan is None or not can_view_plan(actor, plan):
            raise NotFoundError("Plan", payload.plan_slug)
        if plan.status is not PlanStatus.ACTIVE:
            raise ConflictError("Subscriptions are only available for active plans")

        existing = self._subscriptions.active_for_user_plan(
            user_id=actor.id,
            plan_id=plan.id,
        )
        if existing is not None:
            raise ConflictError("You already have an active subscription for this plan")

        now = datetime.now(UTC)
        record = SubscriptionRecord(
            id=self._subscriptions.allocate_id(),
            user_id=actor.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=now,
            current_period_end=_period_end(now, plan.interval),
            created_at=now,
            cancelled_at=None,
        )
        self._subscriptions.add(record)
        return self._to_read(record)

    def cancel(self, actor: UserRead, subscription_id: int) -> SubscriptionRead:
        row = self._subscriptions.get(subscription_id)
        if row is None or not self._can_view(actor, row):
            raise NotFoundError("Subscription", subscription_id)
        if row.status is SubscriptionStatus.CANCELLED:
            raise ConflictError("Subscription is already cancelled")
        if actor.role is not UserRole.ADMIN and row.user_id != actor.id:
            raise ForbiddenError()

        row.status = SubscriptionStatus.CANCELLED
        row.cancelled_at = datetime.now(UTC)
        self._subscriptions.save(row)
        return self._to_read(row)

    def _can_view(self, actor: UserRead, row: SubscriptionRecord) -> bool:
        if actor.role is UserRole.ADMIN:
            return True
        return row.user_id == actor.id

    def _to_read(self, row: SubscriptionRecord) -> SubscriptionRead:
        plan = self._plans.get(row.plan_id)
        user = self._users.get_by_id(row.user_id)
        return SubscriptionRead(
            id=row.id,
            user_id=row.user_id,
            subscriber_name=user.full_name if user else "Unknown",
            plan_id=row.plan_id,
            plan_slug=plan.slug if plan else "unknown",
            plan_name=plan.name if plan else "Unknown plan",
            price_cents=plan.price_cents if plan else 0,
            interval=plan.interval.value if plan else "monthly",
            status=row.status,
            current_period_start=row.current_period_start,
            current_period_end=row.current_period_end,
            created_at=row.created_at,
            cancelled_at=row.cancelled_at,
        )
