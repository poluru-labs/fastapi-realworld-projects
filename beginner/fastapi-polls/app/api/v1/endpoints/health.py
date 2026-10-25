from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/health",
    summary="Health check",
    description="Returns `ok` when the API process is running.",
)
def health_check() -> dict[str, str]:
    return {"status": "ok"}
