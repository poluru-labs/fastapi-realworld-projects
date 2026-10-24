from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/health",
    summary="Health check",
    description="Liveness probe. Returns ok when the process can serve requests.",
)
def health_check() -> dict[str, str]:
    return {"status": "ok"}
