from functools import lru_cache

from app.repositories.unit_repository import UnitRepository
from app.services.conversion_service import ConversionService


@lru_cache
def get_unit_repository() -> UnitRepository:
    return UnitRepository()


def get_conversion_service() -> ConversionService:
    return ConversionService(get_unit_repository())
