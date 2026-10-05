import math
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.unit import Category


class ConversionRequest(BaseModel):
    category: Category = Field(..., description="temperature, distance, or weight")
    value: float = Field(..., description="Quantity to convert. Must be a finite number.")
    from_unit: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="Source unit code or alias, for example celsius or c",
        examples=["celsius"],
    )
    to_unit: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="Target unit code or alias, for example fahrenheit or f",
        examples=["fahrenheit"],
    )

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("from_unit", "to_unit", mode="before")
    @classmethod
    def normalize_unit(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("value", mode="before")
    @classmethod
    def reject_boolean(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("value must be a finite number")
        return value

    @field_validator("value")
    @classmethod
    def finite_value(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("value must be a finite number")
        return value

    @model_validator(mode="after")
    def non_negative_quantity(self) -> Self:
        if self.category in {Category.distance, Category.weight} and self.value < 0:
            raise ValueError(f"{self.category.value} values must be greater than or equal to 0")
        return self


class ConversionRead(BaseModel):
    category: Category
    from_unit: str = Field(
        ...,
        description="Canonical source code, even when the request used an alias",
    )
    to_unit: str = Field(
        ...,
        description="Canonical target code, even when the request used an alias",
    )
    from_symbol: str
    to_symbol: str
    input_value: float = Field(..., description="The number submitted in the request")
    result: float = Field(
        ...,
        description="Converted value, rounded half-up to 6 decimal places when units differ",
    )
    formula: str = Field(..., description="Human-readable rule used for this pair of units")
