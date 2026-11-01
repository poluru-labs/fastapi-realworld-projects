import asyncio
from urllib.parse import urlparse

from app.schemas.monitor import CheckStatus


class ProbeClient:
    """Simulated HTTP probe — no real network calls."""

    async def probe(
        self,
        *,
        target_url: str,
        expected_status: int,
    ) -> tuple[CheckStatus, int | None, int, str]:
        await asyncio.sleep(0)
        parsed = urlparse(target_url)
        path = (parsed.path or "/").casefold()
        host = (parsed.hostname or "").casefold()

        if "down" in path or "down" in host or "fail" in path:
            return CheckStatus.DOWN, 503, 120, "Simulated connection failure"

        if "slow" in path or "degraded" in path:
            latency = 2500
            if expected_status == 200:
                return (
                    CheckStatus.DEGRADED,
                    200,
                    latency,
                    "Response slower than 2s threshold",
                )

        if "404" in path:
            status = 404
            if status != expected_status:
                return (
                    CheckStatus.DOWN,
                    status,
                    45,
                    f"Expected HTTP {expected_status}, got {status}",
                )

        status = 200
        latency = 35
        if status != expected_status:
            return (
                CheckStatus.DOWN,
                status,
                latency,
                f"Expected HTTP {expected_status}, got {status}",
            )
        return CheckStatus.UP, status, latency, "OK"
