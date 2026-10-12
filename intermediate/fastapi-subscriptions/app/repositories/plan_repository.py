from dataclasses import dataclass, field
from datetime import datetime

from app.schemas.plan import BillingInterval, PlanStatus


@dataclass
class PlanRecord:
    id: int
    slug: str
    name: str
    summary: str
    description: str
    price_cents: int
    interval: BillingInterval
    status: PlanStatus
    owner_id: int
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    activated_at: datetime | None = None


def _seed_plans() -> dict[int, PlanRecord]:
    return {
        1: PlanRecord(
            id=1,
            slug="starter-monthly",
            name="Starter",
            summary="For side projects and learning.",
            description="Core API access and community support.",
            price_cents=999,
            interval=BillingInterval.MONTHLY,
            status=PlanStatus.ACTIVE,
            owner_id=1,
            tags=["starter", "monthly"],
            created_at=datetime.fromisoformat("2026-09-01T10:00:00+00:00"),
            updated_at=datetime.fromisoformat("2026-09-10T10:00:00+00:00"),
            activated_at=datetime.fromisoformat("2026-09-10T10:00:00+00:00"),
        ),
        2: PlanRecord(
            id=2,
            slug="pro-yearly",
            name="Pro Yearly",
            summary="Best value for teams shipping often.",
            description="Priority support and advanced quotas.",
            price_cents=9900,
            interval=BillingInterval.YEARLY,
            status=PlanStatus.ACTIVE,
            owner_id=1,
            tags=["pro", "yearly"],
            created_at=datetime.fromisoformat("2026-09-02T10:00:00+00:00"),
            updated_at=datetime.fromisoformat("2026-09-12T10:00:00+00:00"),
            activated_at=datetime.fromisoformat("2026-09-12T10:00:00+00:00"),
        ),
        3: PlanRecord(
            id=3,
            slug="draft-internal",
            name="Internal draft plan",
            summary="Not listed publicly.",
            description="Work in progress pricing.",
            price_cents=0,
            interval=BillingInterval.MONTHLY,
            status=PlanStatus.DRAFT,
            owner_id=1,
            tags=["internal"],
            created_at=datetime.fromisoformat("2026-09-03T10:00:00+00:00"),
            updated_at=datetime.fromisoformat("2026-09-03T10:00:00+00:00"),
            activated_at=None,
        ),
    }


class PlanRepository:
    def __init__(self) -> None:
        self._plans = dict(_seed_plans())
        self._by_slug = {plan.slug: plan for plan in self._plans.values()}
        self._next_id = max(self._plans.keys(), default=0) + 1

    def list_all(self) -> list[PlanRecord]:
        return list(self._plans.values())

    def get(self, plan_id: int) -> PlanRecord | None:
        return self._plans.get(plan_id)

    def get_by_slug(self, slug: str) -> PlanRecord | None:
        return self._by_slug.get(slug)

    def slug_taken(self, slug: str, *, except_id: int | None = None) -> bool:
        existing = self._by_slug.get(slug)
        if existing is None:
            return False
        if except_id is not None and existing.id == except_id:
            return False
        return True

    def add(self, record: PlanRecord) -> PlanRecord:
        self._plans[record.id] = record
        self._by_slug[record.slug] = record
        return record

    def save(self, record: PlanRecord) -> None:
        previous = self._plans.get(record.id)
        if previous is not None and previous.slug != record.slug:
            self._by_slug.pop(previous.slug, None)
        self._plans[record.id] = record
        self._by_slug[record.slug] = record

    def allocate_id(self) -> int:
        plan_id = self._next_id
        self._next_id += 1
        return plan_id
