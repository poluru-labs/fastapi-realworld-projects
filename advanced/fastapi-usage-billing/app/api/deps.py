from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import UnauthorizedError
from app.core.security import hash_api_key
from app.repositories.billing_repository import BillingRepository
from app.schemas.customer import CustomerRead
from app.services.catalog_service import CatalogService
from app.services.customer_service import CustomerService
from app.services.invoice_service import InvoiceService
from app.services.subscription_service import SubscriptionService
from app.services.usage_service import UsageService


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DbSession = Annotated[AsyncSession, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def get_billing_repository(session: DbSession) -> BillingRepository:
    return BillingRepository(session)


def get_customer_service(session: DbSession, settings: AppSettings) -> CustomerService:
    return CustomerService(get_billing_repository(session), settings)


def get_catalog_service(session: DbSession) -> CatalogService:
    return CatalogService(get_billing_repository(session))


def get_subscription_service(session: DbSession) -> SubscriptionService:
    return SubscriptionService(get_billing_repository(session))


def get_usage_service(session: DbSession) -> UsageService:
    return UsageService(get_billing_repository(session))


def get_invoice_service(session: DbSession) -> InvoiceService:
    return InvoiceService(get_billing_repository(session))


async def require_admin(
    settings: AppSettings,
    x_admin_key: Annotated[str | None, Header(alias="X-Admin-Key", include_in_schema=True)] = None,
) -> None:
    if x_admin_key is None or x_admin_key != settings.admin_api_key:
        raise UnauthorizedError("Invalid or missing X-Admin-Key")


async def get_customer_from_api_key(
    settings: AppSettings,
    session: DbSession,
    x_api_key: Annotated[str | None, Header(alias="X-Api-Key", include_in_schema=True)] = None,
) -> CustomerRead:
    if x_api_key is None:
        raise UnauthorizedError("Missing X-Api-Key")
    repo = BillingRepository(session)
    digest = hash_api_key(x_api_key, settings.api_key_pepper)
    record = await repo.get_customer_by_api_key_hash(digest)
    if record is None:
        raise UnauthorizedError("Invalid X-Api-Key")
    return CustomerRead.model_validate(record)


AdminAuth = Annotated[None, Depends(require_admin)]
CustomerAuth = Annotated[CustomerRead, Depends(get_customer_from_api_key)]
