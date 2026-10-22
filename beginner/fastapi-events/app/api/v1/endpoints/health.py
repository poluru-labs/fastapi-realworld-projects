from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/health",
    summary="Liveness probe",
    description="Returns ok when the process is running.",
)
def health_check() -> dict[str, str]:
    return {"status": "ok"}
