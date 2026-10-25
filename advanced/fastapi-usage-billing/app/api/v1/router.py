from fastapi import APIRouter

from app.api.v1.endpoints import (
    customers,
    health,
    invoices,
    me,
    meters,
    plans,
    subscriptions,
    usage,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(meters.router, prefix="/meters", tags=["meters"])
api_router.include_router(plans.router, prefix="/plans", tags=["plans"])
api_router.include_router(
    subscriptions.router,
    prefix="/customers/{customer_id}/subscriptions",
    tags=["subscriptions"],
)
api_router.include_router(usage.router, prefix="/usage", tags=["usage"])
api_router.include_router(
    invoices.router,
    prefix="/customers/{customer_id}/invoices",
    tags=["invoices"],
)
api_router.include_router(me.router, prefix="/me", tags=["me"])
