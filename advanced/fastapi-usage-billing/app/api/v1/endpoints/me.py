from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import (
    CustomerAuth,
    get_invoice_service,
    get_subscription_service,
    get_usage_service,
)
from app.schemas.customer import CustomerRead
from app.schemas.invoice import InvoicePreviewRead
from app.schemas.subscription import SubscriptionRead
from app.schemas.usage import UsageSummaryRead
from app.services.invoice_service import InvoiceService
from app.services.subscription_service import SubscriptionService
from app.services.usage_service import UsageService

router = APIRouter()


@router.get(
    "",
    response_model=CustomerRead,
    summary="Current customer",
    description="Resolve the account behind `X-Api-Key` without exposing the key.",
)
async def read_me(customer: CustomerAuth) -> CustomerRead:
    return customer


@router.get(
    "/usage/summary",
    response_model=UsageSummaryRead,
    summary="My usage totals",
)
async def my_usage_summary(
    customer: CustomerAuth,
    service: Annotated[UsageService, Depends(get_usage_service)],
) -> UsageSummaryRead:
    return await service.usage_summary(customer.id)


@router.get(
    "/subscription",
    response_model=SubscriptionRead,
    summary="My active subscription",
)
async def my_subscription(
    customer: CustomerAuth,
    service: Annotated[SubscriptionService, Depends(get_subscription_service)],
) -> SubscriptionRead:
    return await service.get_active(customer.id)


@router.get(
    "/invoices/preview",
    response_model=InvoicePreviewRead,
    summary="Preview my invoice",
)
async def my_invoice_preview(
    customer: CustomerAuth,
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoicePreviewRead:
    return await service.preview(customer.id)
