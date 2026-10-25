from app.core.exceptions import ConflictError, NotFoundError
from app.db.seed import default_subscription_period
from app.models.billing import Subscription, SubscriptionStatus
from app.repositories.billing_repository import BillingRepository
from app.schemas.subscription import SubscriptionCreate, SubscriptionRead


class SubscriptionService:
    def __init__(self, repo: BillingRepository) -> None:
        self._repo = repo

    async def create_subscription(
        self,
        customer_id: int,
        payload: SubscriptionCreate,
    ) -> SubscriptionRead:
        customer = await self._repo.get_customer(customer_id)
        if customer is None:
            raise NotFoundError("Customer", customer_id)
        plan = await self._repo.get_plan_by_code(payload.plan_code)
        if plan is None:
            raise NotFoundError("Plan", payload.plan_code)
        active = await self._repo.get_active_subscription(customer_id)
        if active is not None:
            raise ConflictError("Customer already has an active subscription")

        start, end = default_subscription_period()
        record = Subscription(
            customer_id=customer_id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE.value,
            current_period_start=start,
            current_period_end=end,
        )
        created = await self._repo.add_subscription(record)
        return SubscriptionRead(
            id=created.id,
            customer_id=created.customer_id,
            plan_code=plan.code,
            status=SubscriptionStatus(created.status),
            current_period_start=created.current_period_start,
            current_period_end=created.current_period_end,
        )

    async def get_active(self, customer_id: int) -> SubscriptionRead:
        record = await self._repo.get_active_subscription(customer_id)
        if record is None:
            raise NotFoundError("Subscription", customer_id)
        return SubscriptionRead(
            id=record.id,
            customer_id=record.customer_id,
            plan_code=record.plan.code,
            status=SubscriptionStatus(record.status),
            current_period_start=record.current_period_start,
            current_period_end=record.current_period_end,
        )
