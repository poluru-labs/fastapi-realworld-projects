from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_book_service
from app.schemas.book import BookCreate, BookDeleteResponse, BookRead, BookUpdate
from app.services.book_service import BookService

router = APIRouter()

_CREATE_EXAMPLES = {
    "full": {
        "summary": "Book with ISBN",
        "description": "ISBN must be unique when provided. Hyphens are allowed.",
        "value": {
            "title": "Designing Data-Intensive Applications",
            "author": "Martin Kleppmann",
            "isbn": "978-1449373320",
            "genre": "Software",
            "publication_year": 2017,
            "available": True,
            "featured": False,
        },
    },
    "no_isbn": {
        "summary": "Title and author only",
        "value": {
            "title": "Local author anthology",
            "author": "Various",
            "genre": "Fiction",
        },
    },
}

_UPDATE_EXAMPLES = {
    "availability": {
        "summary": "Mark checked out",
        "value": {"available": False},
    },
    "clear_isbn": {
        "summary": "Remove ISBN from record",
        "value": {"isbn": ""},
    },
}


@router.get(
    "/genres",
    response_model=list[str],
    summary="List distinct genres",
    description="Sorted alphabetically from books currently in the catalog.",
)
def list_genres(service: Annotated[BookService, Depends(get_book_service)]) -> list[str]:
    return service.list_genres()


@router.get(
    "",
    response_model=list[BookRead],
    summary="List books",
    description=(
        "Featured titles appear first, then smaller ids. "
        "Filter with `genre`, `available`, `featured`, and `search`. "
        "`search` matches title, author, or ISBN (ignoring case and hyphens in ISBN)."
    ),
)
def list_books(
    service: Annotated[BookService, Depends(get_book_service)],
    genre: Annotated[str | None, Query(description="Exact genre match (case insensitive).")] = None,
    search: Annotated[str | None, Query(description="Substring search.")] = None,
    available: Annotated[bool | None, Query(description="Filter by shelf availability.")] = None,
    featured: Annotated[bool | None, Query(description="Filter featured titles.")] = None,
) -> list[BookRead]:
    return service.list_books(genre=genre, search=search, available=available, featured=featured)


@router.get("/{book_id}", response_model=BookRead, summary="Get one book")
def get_book(
    book_id: int,
    service: Annotated[BookService, Depends(get_book_service)],
) -> BookRead:
    return service.get_book(book_id)


@router.post(
    "",
    response_model=BookRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a book",
)
def create_book(
    service: Annotated[BookService, Depends(get_book_service)],
    payload: Annotated[BookCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
) -> BookRead:
    return service.create_book(payload)


@router.put("/{book_id}", response_model=BookRead, summary="Replace a book")
def replace_book(
    book_id: int,
    payload: BookCreate,
    service: Annotated[BookService, Depends(get_book_service)],
) -> BookRead:
    return service.replace_book(book_id, payload)


@router.patch(
    "/{book_id}",
    response_model=BookRead,
    summary="Partial update",
)
def update_book(
    book_id: int,
    service: Annotated[BookService, Depends(get_book_service)],
    payload: Annotated[BookUpdate, Body(openapi_examples=_UPDATE_EXAMPLES)],
) -> BookRead:
    return service.update_book(book_id, payload)


@router.post("/{book_id}/feature", response_model=BookRead, summary="Mark as featured")
def feature_book(
    book_id: int,
    service: Annotated[BookService, Depends(get_book_service)],
) -> BookRead:
    return service.feature_book(book_id)


@router.post("/{book_id}/unfeature", response_model=BookRead, summary="Remove featured flag")
def unfeature_book(
    book_id: int,
    service: Annotated[BookService, Depends(get_book_service)],
) -> BookRead:
    return service.unfeature_book(book_id)


@router.delete("/{book_id}", response_model=BookDeleteResponse, summary="Remove from catalog")
def delete_book(
    book_id: int,
    service: Annotated[BookService, Depends(get_book_service)],
) -> BookDeleteResponse:
    removed = service.delete_book(book_id)
    return BookDeleteResponse(book=removed)
