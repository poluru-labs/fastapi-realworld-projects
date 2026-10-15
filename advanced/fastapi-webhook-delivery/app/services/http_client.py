import httpx


def default_webhook_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))
