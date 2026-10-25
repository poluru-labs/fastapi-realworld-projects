from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import AdminAuth, get_invoice_service
from app.schemas.invoice import InvoicePreviewRead, InvoiceRead
from app.services.invoice_service import InvoiceService

router = APIRouter()


@router.get(
    "/preview",
    response_model=InvoicePreviewRead,
    summary="Preview invoice",
    description=(
        "Compute overage lines from usage in the active billing period. "
        "Nothing is written to the database."
    ),
    responses={404: {"description": "Customer or subscription not found"}},
)
async def preview_invoice(
    customer_id: int,
    _admin: AdminAuth,
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoicePreviewRead:
    return await service.preview(customer_id)


@router.post(
    "",
    response_model=InvoiceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Generate invoice",
    description=(
        "Persist the preview for the current period. "
        "Repeating for the same period returns 409."
    ),
    responses={
        404: {"description": "Customer or subscription not found"},
        409: {"description": "Invoice already exists for this period"},
    },
)
async def generate_invoice(
    customer_id: int,
    _admin: AdminAuth,
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoiceRead:
    return await service.generate(customer_id)


@router.get(
    "",
    response_model=list[InvoiceRead],
    summary="List invoices",
    responses={404: {"description": "Customer not found"}},
)
async def list_invoices(
    customer_id: int,
    _admin: AdminAuth,
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> list[InvoiceRead]:
    return await service.list_invoices(customer_id)
