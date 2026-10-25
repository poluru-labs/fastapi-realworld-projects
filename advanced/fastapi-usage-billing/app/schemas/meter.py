from pydantic import BaseModel, ConfigDict, Field


class MeterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str = Field(..., examples=["api_calls"])
    display_name: str
    unit: str
    description: str
