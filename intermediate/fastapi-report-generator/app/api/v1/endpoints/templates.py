from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_report_service
from app.schemas.report import TemplateCreate, TemplateRead, TemplateUpdate
from app.schemas.user import UserRead
from app.services.report_service import ReportService

router = APIRouter()


@router.get(
    "",
    response_model=list[TemplateRead],
    summary="List report templates",
    description="Users see their templates. Platform admin sees all templates.",
)
def list_templates(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ReportService, Depends(get_report_service)],
) -> list[TemplateRead]:
    return service.list_templates(current_user)


@router.post(
    "",
    response_model=TemplateRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a template",
)
def create_template(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ReportService, Depends(get_report_service)],
    payload: TemplateCreate,
) -> TemplateRead:
    return service.create_template(current_user, payload)


@router.get(
    "/{template_id}",
    response_model=TemplateRead,
    summary="Get a template",
    description="Returns **404** when the template is missing or owned by another user.",
)
def get_template(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ReportService, Depends(get_report_service)],
    template_id: int,
) -> TemplateRead:
    return service.get_template(current_user, template_id)


@router.patch(
    "/{template_id}",
    response_model=TemplateRead,
    summary="Update a template",
    description="Only the owner may edit. Admins can read but not patch others' templates.",
)
def update_template(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ReportService, Depends(get_report_service)],
    template_id: int,
    payload: TemplateUpdate,
) -> TemplateRead:
    return service.update_template(current_user, template_id, payload)


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a template",
)
def delete_template(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ReportService, Depends(get_report_service)],
    template_id: int,
) -> None:
    service.delete_template(current_user, template_id)
