from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.api.deps import get_conversion_service
from app.schemas.unit import Category, CategoryUnitsRead
from app.services.conversion_service import ConversionService

router = APIRouter()


@router.get(
    "",
    response_model=list[CategoryUnitsRead],
    summary="List supported categories and units",
    description=(
        "Returns temperature, distance, and weight with every unit code, symbol, alias, "
        "and scale factor. Call this before converting when you need the accepted codes."
    ),
)
def list_units(
    service: Annotated[ConversionService, Depends(get_conversion_service)],
) -> list[CategoryUnitsRead]:
    return service.list_categories()


@router.get(
    "/{category}",
    response_model=CategoryUnitsRead,
    summary="List units in one category",
    description=(
        "Returns the pivot unit and the codes accepted for that category. "
        "`factor_to_base` is an exact decimal string for distance and weight, and null "
        "for temperature."
    ),
    responses={
        422: {"description": "Category must be temperature, distance, or weight."},
    },
)
def get_category_units(
    category: Annotated[
        Category,
        Path(description="One of temperature, distance, or weight"),
    ],
    service: Annotated[ConversionService, Depends(get_conversion_service)],
) -> CategoryUnitsRead:
    return service.get_category(category)
