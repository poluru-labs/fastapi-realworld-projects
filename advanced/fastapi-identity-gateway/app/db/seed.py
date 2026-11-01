from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, hash_secret
from app.models.identity import OAuthClient, User
from app.schemas.identity import GrantType, OAuthScope

SEED_EMAIL = "demo@example.com"
SEED_PASSWORD = "DemoPass123!"
SEED_CLIENT_ID = "cli_seed_dashboard"
SEED_CLIENT_SECRET = "cs_seed_secret_for_tests_only_32chars"


async def seed_reference_data(session: AsyncSession, *, pepper: str) -> None:
    user_exists = await session.scalar(select(User.id).where(User.email == SEED_EMAIL))
    if user_exists is None:
        session.add(
            User(
                email=SEED_EMAIL,
                hashed_password=hash_password(SEED_PASSWORD),
                full_name="Demo User",
            )
        )

    client_exists = await session.scalar(
        select(OAuthClient.id).where(OAuthClient.client_id == SEED_CLIENT_ID)
    )
    if client_exists is None:
        session.add(
            OAuthClient(
                client_id=SEED_CLIENT_ID,
                client_secret_hash=hash_secret(SEED_CLIENT_SECRET, pepper=pepper),
                name="Dashboard (seed)",
                grant_types=[
                    GrantType.AUTHORIZATION_CODE.value,
                    GrantType.CLIENT_CREDENTIALS.value,
                    GrantType.REFRESH_TOKEN.value,
                ],
                allowed_scopes=[
                    OAuthScope.OPENID.value,
                    OAuthScope.PROFILE.value,
                    OAuthScope.EMAIL.value,
                    OAuthScope.API_READ.value,
                ],
                redirect_uris=["http://127.0.0.1:3000/callback"],
                is_confidential=True,
            )
        )

    await session.commit()
