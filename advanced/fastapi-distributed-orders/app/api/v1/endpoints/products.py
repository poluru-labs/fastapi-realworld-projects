from fastapi import APIRouter, status

from app.api.deps import AdminUser, DbSession
from app.schemas.product import ProductCreate, ProductRead
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.get(
    "",
    response_model=list[ProductRead],
    summary="Catalog with live stock counts",
    description="Public catalog read. Stock reflects reservations from pending orders.",
)
async def list_products(session: DbSession) -> list[ProductRead]:
    return await ProductService(session).list_products()


@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a SKU (admin)",
)
async def create_product(
    payload: ProductCreate,
    actor: AdminUser,
    session: DbSession,
) -> ProductRead:
    return await ProductService(session).create_product(actor, payload)
