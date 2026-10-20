from pydantic import BaseModel, Field


class HealthLive(BaseModel):
    status: str = Field(..., examples=["ok"])


class HealthReady(BaseModel):
    status: str = Field(..., examples=["ok"])
    database: str = Field(..., examples=["ok"])
