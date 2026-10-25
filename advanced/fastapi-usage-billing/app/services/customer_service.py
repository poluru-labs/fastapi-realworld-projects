from app.core.config import Settings
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import generate_api_key, hash_api_key
from app.models.billing import Customer
from app.repositories.billing_repository import BillingRepository
from app.schemas.customer import CustomerCreate, CustomerCreated, CustomerRead


class CustomerService:
    def __init__(self, repo: BillingRepository, settings: Settings) -> None:
        self._repo = repo
        self._settings = settings

    async def create_customer(self, payload: CustomerCreate) -> CustomerCreated:
        if await self._repo.get_customer_by_external_id(payload.external_id) is not None:
            raise ConflictError("A customer with this external_id already exists")
        api_key = generate_api_key()
        record = Customer(
            external_id=payload.external_id,
            name=payload.name,
            api_key_hash=hash_api_key(api_key, self._settings.api_key_pepper),
        )
        created = await self._repo.add_customer(record)
        return CustomerCreated(
            id=created.id,
            external_id=created.external_id,
            name=created.name,
            created_at=created.created_at,
            api_key=api_key,
        )

    async def get_customer(self, customer_id: int) -> CustomerRead:
        record = await self._repo.get_customer(customer_id)
        if record is None:
            raise NotFoundError("Customer", customer_id)
        return CustomerRead.model_validate(record)

    async def list_customers(self) -> list[CustomerRead]:
        rows = await self._repo.list_customers()
        return [CustomerRead.model_validate(row) for row in rows]
