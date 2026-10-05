from typing import Annotated

from fastapi import APIRouter, Body, Depends

from app.api.deps import get_conversion_service
from app.schemas.conversion import ConversionRead, ConversionRequest
from app.services.conversion_service import ConversionService

router = APIRouter()

_EXAMPLES = {
    "boiling_point": {
        "summary": "100 °C to °F",
        "description": "Water's boiling point at standard atmospheric pressure.",
        "value": {
            "category": "temperature",
            "value": 100,
            "from_unit": "celsius",
            "to_unit": "fahrenheit",
        },
    },
    "freezing_alias": {
        "summary": "0 °C to °F using aliases",
        "description": "Short codes c and f are aliases for celsius and fahrenheit.",
        "value": {
            "category": "temperature",
            "value": 0,
            "from_unit": "c",
            "to_unit": "f",
        },
    },
    "inch_to_centimeter": {
        "summary": "1 inch to centimeters",
        "description": "1 inch is defined as exactly 2.54 centimeters.",
        "value": {
            "category": "distance",
            "value": 1,
            "from_unit": "inch",
            "to_unit": "centimeter",
        },
    },
    "kilogram_to_pound": {
        "summary": "1 kilogram to pounds",
        "description": "Uses the international avoirdupois pound (453.59237 g).",
        "value": {
            "category": "weight",
            "value": 1,
            "from_unit": "kg",
            "to_unit": "lb",
        },
    },
}


@router.post(
    "",
    response_model=ConversionRead,
    summary="Convert a value between two units",
    response_description="Converted value, canonical unit codes, and the formula that was applied",
    description=(
        "Both units must belong to `category`. Codes are case-insensitive and may be "
        "the canonical name (`celsius`) or an alias (`c`, `degc`). "
        "Distance and weight must be zero or positive. "
        "Temperature must be at or above absolute zero (−273.15 °C). "
        "When the units differ, `result` is rounded half-up to 6 decimal places."
    ),
    responses={
        400: {"description": "The unit code is not recognized for that category."},
        422: {
            "description": (
                "The body failed validation, or the temperature is below absolute zero."
            )
        },
    },
)
def convert_value(
    payload: Annotated[ConversionRequest, Body(openapi_examples=_EXAMPLES)],
    service: Annotated[ConversionService, Depends(get_conversion_service)],
) -> ConversionRead:
    return service.convert(payload)
