from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    response_json: Mapped[str] = mapped_column(Text)
    status_code: Mapped[int] = mapped_column(Integer, default=201)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
