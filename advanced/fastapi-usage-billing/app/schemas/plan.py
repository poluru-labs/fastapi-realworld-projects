from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PlanMeterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    meter_code: str
    included_quantity: Decimal = Field(..., description="Units included each billing period")
    unit_price_cents: int = Field(..., description="Overage price in cents per unit")


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str
    meters: list[PlanMeterRead]
