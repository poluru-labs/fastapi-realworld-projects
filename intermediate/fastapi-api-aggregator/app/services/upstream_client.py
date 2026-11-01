import asyncio

from app.schemas.source import MockCatalog

_MOCK_CATALOG: dict[MockCatalog, dict[str, dict]] = {
    MockCatalog.USERS: {
        "/v1/profile": {"user_id": "u_42", "email": "demo@example.com", "plan": "pro"},
        "/v1/preferences": {"theme": "dark", "locale": "en-US"},
    },
    MockCatalog.ORDERS: {
        "/v1/recent": {
            "orders": [
                {"id": "ord_100", "total_cents": 2599, "status": "shipped"},
                {"id": "ord_99", "total_cents": 1200, "status": "delivered"},
            ]
        },
    },
    MockCatalog.INVENTORY: {
        "/v1/low-stock": {"skus": [{"sku": "sku-12", "qty": 3}, {"sku": "sku-44", "qty": 1}]},
    },
}


class UpstreamClient:
    """Simulated upstream HTTP — paths resolve against in-memory mock catalogs."""

    async def fetch(
        self,
        *,
        catalog: MockCatalog,
        path: str,
        method: str,
    ) -> tuple[int, dict | None, str | None]:
        if method != "GET":
            return 405, None, f"Mock upstream only supports GET, got {method}"

        await asyncio.sleep(0)
        routes = _MOCK_CATALOG.get(catalog, {})
        payload = routes.get(path)
        if payload is None:
            return 404, None, f"No mock response for {catalog.value}{path}"
        return 200, payload, None
