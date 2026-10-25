from app.core.exceptions import NotFoundError
from app.repositories.billing_repository import BillingRepository
from app.schemas.meter import MeterRead
from app.schemas.plan import PlanMeterRead, PlanRead


class CatalogService:
    def __init__(self, repo: BillingRepository) -> None:
        self._repo = repo

    async def list_meters(self) -> list[MeterRead]:
        rows = await self._repo.list_meters()
        return [MeterRead.model_validate(row) for row in rows]

    async def list_plans(self) -> list[PlanRead]:
        rows = await self._repo.list_plans()
        return [self._plan_to_read(plan) for plan in rows]

    async def get_plan(self, plan_code: str) -> PlanRead:
        plan = await self._repo.get_plan_by_code(plan_code)
        if plan is None:
            raise NotFoundError("Plan", plan_code)
        return self._plan_to_read(plan)

    def _plan_to_read(self, plan) -> PlanRead:
        meters = [
            PlanMeterRead(
                meter_code=pm.meter.code,
                included_quantity=pm.included_quantity,
                unit_price_cents=pm.unit_price_cents,
            )
            for pm in plan.plan_meters
        ]
        return PlanRead(
            id=plan.id,
            code=plan.code,
            name=plan.name,
            description=plan.description,
            meters=meters,
        )
