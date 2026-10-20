"""Load demo devices and readings after `alembic upgrade head`. Safe to re-run."""

import asyncio

from app.core.config import get_settings
from app.db.seed import seed_reference_data
from app.db.session import make_engine, make_session_factory


async def main() -> None:
    settings = get_settings()
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    async with session_factory() as session:
        await seed_reference_data(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
