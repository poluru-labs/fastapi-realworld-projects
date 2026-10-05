from enum import StrEnum

from pydantic import BaseModel, Field


class Category(StrEnum):
    """Conversion family. Units never convert across categories."""

    temperature = "temperature"
    distance = "distance"
    weight = "weight"


class UnitRead(BaseModel):
    code: str = Field(..., description="Canonical unit code to send to the convert endpoint")
    symbol: str = Field(..., description="Display symbol, such as °C or km")
    name: str = Field(..., description="English name")
    aliases: list[str] = Field(
        ...,
        description="Extra codes accepted in convert requests. Matching is case-insensitive.",
    )
    factor_to_base: str | None = Field(
        None,
        description=(
            "Exact decimal scale factor. Multiply a quantity in this unit by the factor "
            "to get the category base unit. Null for temperature, which uses offset "
            "formulas instead of a single factor."
        ),
    )


class CategoryUnitsRead(BaseModel):
    category: Category
    description: str
    base_unit: str = Field(..., description="Unit code used as the conversion pivot")
    units: list[UnitRead]
