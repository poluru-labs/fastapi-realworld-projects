from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class OutboxEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    aggregate_type: str
    aggregate_id: int
    payload: dict[str, Any]
    created_at: datetime
    published_at: datetime | None
