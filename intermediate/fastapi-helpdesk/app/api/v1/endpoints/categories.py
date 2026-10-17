from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_ticket_service
from app.schemas.ticket import CategoryCount
from app.services.ticket_service import TicketService

router = APIRouter()


@router.get(
    "",
    response_model=list[CategoryCount],
    summary="List categories (tags) on submitted tickets",
)
def list_categories(
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> list[CategoryCount]:
    return service.list_categories()
