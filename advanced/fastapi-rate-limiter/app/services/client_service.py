from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.client_tokens import generate_client_key, hash_client_key, verify_client_key
from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.core.windows import fixed_window_start
from app.models.rate_limiting import RateLimitClient
from app.repositories.rate_limit_repository import RateLimitRepository
from app.schemas.rate_limiting import ClientCreate, ClientProvisioned, ClientRead, SubjectUsageRow


class ClientService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = RateLimitRepository(session)

    async def list_clients(self) -> list[ClientRead]:
        rows = await self._repo.list_clients()
        reads: list[ClientRead] = []
        for row in rows:
            reads.append(await self._read_client(row))
        return reads

    async def provision(self, payload: ClientCreate) -> ClientProvisioned:
        if await self._repo.get_client_by_key(payload.key) is not None:
            raise ConflictError(f"Client key {payload.key!r} already exists")
        policy = await self._repo.get_policy_by_key(payload.policy_key)
        if policy is None:
            raise NotFoundError("Policy", payload.policy_key)

        plaintext = generate_client_key()
        client = RateLimitClient(
            key=payload.key,
            name=payload.name,
            policy_id=policy.id,
            client_key_hash=hash_client_key(plaintext),
            created_at=datetime.now(UTC),
        )
        await self._repo.add_client(client)
        await self._session.commit()
        base = await self._read_client(client)
        return ClientProvisioned(**base.model_dump(), client_key=plaintext)

    async def get_client(self, client_key: str) -> ClientRead:
        client = await self._require_client(client_key)
        return await self._read_client(client)

    async def usage_snapshot(self, client_key: str) -> list[SubjectUsageRow]:
        client = await self._require_client(client_key)
        policy = await self._repo.get_policy_by_id(client.policy_id)
        if policy is None:
            raise NotFoundError("Policy", client.policy_id)

        window_start = fixed_window_start(datetime.now(UTC), policy.window_seconds)
        counters = await self._repo.list_counters_for_client(client.id, window_start)
        rows = sorted(counters, key=lambda row: row.subject_key)
        return [
            SubjectUsageRow(
                subject_key=row.subject_key,
                window_count=row.count,
                remaining=max(0, policy.limit - row.count),
            )
            for row in rows
        ]

    async def verify_client_key(self, client_key_slug: str, presented_key: str) -> RateLimitClient:
        client = await self._repo.get_client_by_key(client_key_slug)
        if client is None:
            raise NotFoundError("Client", client_key_slug)
        if not verify_client_key(presented_key, client.client_key_hash):
            raise UnauthorizedError("Invalid X-Client-Key")
        return client

    async def _require_client(self, client_key: str) -> RateLimitClient:
        client = await self._repo.get_client_by_key(client_key)
        if client is None:
            raise NotFoundError("Client", client_key)
        return client

    async def _read_client(self, client: RateLimitClient) -> ClientRead:
        policy = await self._repo.get_policy_by_id(client.policy_id)
        if policy is None:
            raise NotFoundError("Policy", client.policy_id)
        return ClientRead(
            id=client.id,
            key=client.key,
            name=client.name,
            policy_key=policy.key,
            policy_limit=policy.limit,
            window_seconds=policy.window_seconds,
        )
