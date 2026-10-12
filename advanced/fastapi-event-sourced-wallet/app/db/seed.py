from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User
from app.models.wallet import Wallet, WalletEvent
from app.schemas.user import UserRole
from app.schemas.wallet import WalletEventType


async def seed_reference_data(session: AsyncSession) -> None:
    admin = await session.scalar(select(User).where(User.email == "admin@example.com"))
    if admin is None:
        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("AdminPass123!"),
            full_name="Wallet Admin",
            role=UserRole.ADMIN.value,
            is_active=True,
        )
        session.add(admin)
        await session.flush()

    demo = await session.scalar(
        select(Wallet).where(Wallet.owner_id == admin.id, Wallet.name == "Demo Treasury")
    )
    if demo is None:
        wallet_id = str(uuid4())
        demo = Wallet(
            id=wallet_id,
            owner_id=admin.id,
            name="Demo Treasury",
            currency="USD",
            balance_cents=100_000,
            version=2,
        )
        session.add(demo)
        session.add_all(
            [
                WalletEvent(
                    wallet_id=wallet_id,
                    sequence=1,
                    event_type=WalletEventType.WALLET_CREATED.value,
                    payload={
                        "name": "Demo Treasury",
                        "currency": "USD",
                        "owner_id": admin.id,
                    },
                ),
                WalletEvent(
                    wallet_id=wallet_id,
                    sequence=2,
                    event_type=WalletEventType.MONEY_DEPOSITED.value,
                    payload={
                        "amount_cents": 100_000,
                        "memo": "Seed funding",
                    },
                ),
            ]
        )

    await session.commit()
