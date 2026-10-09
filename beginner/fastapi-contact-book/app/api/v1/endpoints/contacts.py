from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_contact_service
from app.schemas.contact import (
    ContactCreate,
    ContactDeleteResponse,
    ContactRead,
    ContactUpdate,
)
from app.services.contact_service import ContactService

router = APIRouter()

_CREATE_EXAMPLES = {
    "full": {
        "summary": "Contact with email",
        "description": "Email must be unique when provided. Omit email for phone-only entries.",
        "value": {
            "full_name": "Sam Rivera",
            "email": "sam@example.com",
            "phone": "+1-555-0142",
            "company": "Rivera Design",
            "notes": "Met at the FastAPI meetup.",
        },
    },
    "phone_only": {
        "summary": "No email",
        "value": {
            "full_name": "Desk phone",
            "phone": "+1-555-0000",
            "company": "Office",
        },
    },
}

_UPDATE_EXAMPLES = {
    "company": {
        "summary": "Change company only",
        "description": "Omitted fields stay as they are.",
        "value": {"company": "Analytical Engines Ltd"},
    },
    "clear_email": {
        "summary": "Remove an email address",
        "value": {"email": ""},
    },
}


@router.get(
    "",
    response_model=list[ContactRead],
    summary="List contacts",
    description=(
        "Favorites appear first, then smaller ids. "
        "Pass favorite=true or false to filter. "
        "Pass search to match full_name, email, phone, company, or notes, ignoring case. "
        "A blank search is ignored."
    ),
)
def list_contacts(
    service: Annotated[ContactService, Depends(get_contact_service)],
    favorite: Annotated[
        bool | None,
        Query(description="true for favorites only, false for everyone else."),
    ] = None,
    search: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=80,
            description="Case-insensitive text search across contact fields.",
        ),
    ] = None,
) -> list[ContactRead]:
    return service.list_contacts(favorite=favorite, search=search)


@router.get(
    "/{contact_id}",
    response_model=ContactRead,
    summary="Get a contact",
    responses={404: {"description": "No contact has that id."}},
)
def get_contact(
    contact_id: int,
    service: Annotated[ContactService, Depends(get_contact_service)],
) -> ContactRead:
    return service.get_contact(contact_id)


@router.post(
    "",
    response_model=ContactRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a contact",
    description=(
        "full_name is required, 1–120 characters after trimming spaces. "
        "email is optional and must be unique when set. "
        "favorite defaults to false."
    ),
    responses={
        409: {"description": "Another contact already uses this email."},
        422: {"description": "The body failed validation."},
    },
)
def create_contact(
    payload: Annotated[ContactCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
    service: Annotated[ContactService, Depends(get_contact_service)],
) -> ContactRead:
    return service.create_contact(payload)


@router.patch(
    "/{contact_id}",
    response_model=ContactRead,
    summary="Update a contact",
    description=(
        "Send only the fields you want to change. "
        "An empty body returns the contact unchanged. "
        "Send email as an empty string to clear it."
    ),
    responses={
        404: {"description": "No contact has that id."},
        409: {"description": "Email is already used by another contact."},
    },
)
def update_contact(
    contact_id: int,
    payload: Annotated[ContactUpdate, Body(openapi_examples=_UPDATE_EXAMPLES)],
    service: Annotated[ContactService, Depends(get_contact_service)],
) -> ContactRead:
    return service.update_contact(contact_id, payload)


@router.post(
    "/{contact_id}/favorite",
    response_model=ContactRead,
    summary="Mark as favorite",
    description="Sets favorite to true. Calling again on a favorite leaves the contact as it is.",
    responses={404: {"description": "No contact has that id."}},
)
def favorite_contact(
    contact_id: int,
    service: Annotated[ContactService, Depends(get_contact_service)],
) -> ContactRead:
    return service.favorite_contact(contact_id)


@router.post(
    "/{contact_id}/unfavorite",
    response_model=ContactRead,
    summary="Remove from favorites",
    description=(
        "Sets favorite to false. Calling again on a non-favorite leaves the contact as it is."
    ),
    responses={404: {"description": "No contact has that id."}},
)
def unfavorite_contact(
    contact_id: int,
    service: Annotated[ContactService, Depends(get_contact_service)],
) -> ContactRead:
    return service.unfavorite_contact(contact_id)


@router.delete(
    "/{contact_id}",
    response_model=ContactDeleteResponse,
    summary="Delete a contact",
    description="Removes the contact and returns a snapshot of what was deleted.",
    responses={404: {"description": "No contact has that id."}},
)
def delete_contact(
    contact_id: int,
    service: Annotated[ContactService, Depends(get_contact_service)],
) -> ContactDeleteResponse:
    removed = service.delete_contact(contact_id)
    return ContactDeleteResponse(contact=removed)
