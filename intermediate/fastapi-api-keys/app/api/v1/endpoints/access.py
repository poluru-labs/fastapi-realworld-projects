from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import PrincipalDep, get_access_service
from app.schemas.access import MetricsRead, WhoamiRead
from app.schemas.project import ProjectCreate, ProjectRead
from app.services.access_service import AccessService

router = APIRouter()


@router.get(
    "/whoami",
    response_model=WhoamiRead,
    summary="Identify the caller",
    description=(
        "Accepts `Authorization: Bearer` **or** `X-Api-Key`. "
        "When both headers are sent, the API key takes precedence."
    ),
    responses={401: {"description": "Missing or invalid credentials."}},
)
def whoami(
    principal: PrincipalDep,
    service: Annotated[AccessService, Depends(get_access_service)],
) -> WhoamiRead:
    return service.whoami(principal)


@router.get(
    "/projects",
    response_model=list[ProjectRead],
    summary="List your projects",
    description=(
        "Requires scope `projects:read` when using an API key. JWT callers bypass scope checks."
    ),
    responses={403: {"description": "API key lacks `projects:read`."}},
)
def list_projects(
    principal: PrincipalDep,
    service: Annotated[AccessService, Depends(get_access_service)],
) -> list[ProjectRead]:
    return service.list_projects(principal)


@router.post(
    "/projects",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
    description="Requires scope `projects:write` for API keys.",
)
def create_project(
    payload: ProjectCreate,
    principal: PrincipalDep,
    service: Annotated[AccessService, Depends(get_access_service)],
) -> ProjectRead:
    return service.create_project(principal, payload)


@router.get(
    "/metrics",
    response_model=MetricsRead,
    summary="Account metrics",
    description="Requires scope `metrics:read` for API keys.",
)
def read_metrics(
    principal: PrincipalDep,
    service: Annotated[AccessService, Depends(get_access_service)],
) -> MetricsRead:
    return service.metrics(principal)
