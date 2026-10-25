from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import AdminAuth, get_customer_service
from app.schemas.customer import CustomerCreate, CustomerCreated, CustomerRead
from app.services.customer_service import CustomerService

router = APIRouter()


@router.post(
    "",
    response_model=CustomerCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Create customer",
    description=(
        "Platform admin only. Returns a one-time `api_key` for usage ingestion. "
        "Store it securely; the API never returns the raw key again."
    ),
    responses={409: {"description": "external_id already exists"}},
)
async def create_customer(
    payload: CustomerCreate,
    _admin: AdminAuth,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> CustomerCreated:
    return await service.create_customer(payload)


@router.get(
    "",
    response_model=list[CustomerRead],
    summary="List customers",
    description="Platform admin only.",
)
async def list_customers(
    _admin: AdminAuth,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> list[CustomerRead]:
    return await service.list_customers()


@router.get(
    "/{customer_id}",
    response_model=CustomerRead,
    summary="Get customer",
    responses={404: {"description": "Customer not found"}},
)
async def get_customer(
    customer_id: int,
    _admin: AdminAuth,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> CustomerRead:
    return await service.get_customer(customer_id)
