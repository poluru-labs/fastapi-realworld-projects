from app.repositories.product_repository import ProductRepository
from app.schemas.product import (
    CategoryListResponse,
    ProductCreate,
    ProductDeleteResponse,
    ProductRead,
    ProductUpdate,
)


class ProductService:
    def __init__(self, repo: ProductRepository) -> None:
        self._repo = repo

    def list_categories(self) -> CategoryListResponse:
        return CategoryListResponse(categories=self._repo.list_categories())

    def list_products(
        self,
        *,
        category: str | None,
        search: str | None,
        in_stock: bool | None,
        featured: bool | None,
        discontinued: bool,
    ) -> list[ProductRead]:
        rows = self._repo.list_products(
            category=category,
            search=search,
            in_stock=in_stock,
            featured=featured,
            discontinued=discontinued,
        )
        return [ProductRead.model_validate(r) for r in rows]

    def get_product(self, product_id: int) -> ProductRead:
        return ProductRead.model_validate(self._repo.get(product_id))

    def get_by_sku(self, sku: str) -> ProductRead:
        return ProductRead.model_validate(self._repo.get_by_sku(sku))

    def create_product(self, payload: ProductCreate) -> ProductRead:
        record = self._repo.create(
            sku=payload.sku,
            name=payload.name,
            description=payload.description,
            price=payload.price,
            category=payload.category,
            tags=payload.tags,
            stock_quantity=payload.stock_quantity,
            featured=payload.featured,
        )
        return ProductRead.model_validate(record)

    def update_product(self, product_id: int, payload: ProductUpdate) -> ProductRead:
        record = self._repo.update(
            product_id,
            name=payload.name,
            description=payload.description,
            price=payload.price,
            category=payload.category,
            tags=payload.tags,
            stock_quantity=payload.stock_quantity,
            featured=payload.featured,
        )
        return ProductRead.model_validate(record)

    def feature(self, product_id: int) -> ProductRead:
        return ProductRead.model_validate(self._repo.set_featured(product_id, featured=True))

    def unfeature(self, product_id: int) -> ProductRead:
        return ProductRead.model_validate(self._repo.set_featured(product_id, featured=False))

    def discontinue(self, product_id: int) -> ProductRead:
        return ProductRead.model_validate(
            self._repo.set_discontinued(product_id, discontinued=True)
        )

    def restore(self, product_id: int) -> ProductRead:
        return ProductRead.model_validate(
            self._repo.set_discontinued(product_id, discontinued=False)
        )

    def delete_product(self, product_id: int) -> ProductDeleteResponse:
        self._repo.delete(product_id)
        return ProductDeleteResponse(id=product_id)
