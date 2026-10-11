from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.event import Event, EventStatus, TicketTier
from app.models.user import User, UserRole
from app.models.venue import Venue


async def seed_reference_data(session: AsyncSession) -> None:
    admin = await session.scalar(select(User).where(User.email == "admin@example.com"))
    if admin is None:
        session.add(
            User(
                email="admin@example.com",
                hashed_password=hash_password("AdminPass123!"),
                full_name="Box Office Admin",
                role=UserRole.ADMIN.value,
                is_active=True,
            )
        )

    venue = await session.scalar(select(Venue).where(Venue.name == "Grand Hall"))
    if venue is None:
        venue = Venue(name="Grand Hall", city="Austin")
        session.add(venue)
        await session.flush()

    event = await session.scalar(select(Event).where(Event.slug == "jazz-night"))
    if event is None:
        event = Event(
            slug="jazz-night",
            title="Jazz Night Live",
            description="An evening of modern jazz.",
            venue_id=venue.id,
            starts_at=datetime.fromisoformat("2026-12-20T20:00:00+00:00"),
            status=EventStatus.PUBLISHED.value,
        )
        session.add(event)
        await session.flush()
        session.add_all(
            [
                TicketTier(
                    event_id=event.id,
                    name="General Admission",
                    price_cents=3500,
                    capacity=100,
                ),
                TicketTier(
                    event_id=event.id,
                    name="VIP",
                    price_cents=9500,
                    capacity=20,
                ),
            ]
        )

    await session.commit()
