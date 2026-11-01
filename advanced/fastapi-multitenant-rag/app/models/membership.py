from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TenantRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class TenantMembership(Base):
    __tablename__ = "tenant_memberships"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", name="uq_membership"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16), default=TenantRole.MEMBER.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
