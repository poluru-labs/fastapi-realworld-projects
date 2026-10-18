from app.repositories.product_repository import get_product_repository
from app.services.product_service import ProductService


def get_product_service() -> ProductService:
    return ProductService(get_product_repository())
