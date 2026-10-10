from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.book_repository import BookRepository
from app.schemas.book import BookCreate, BookRead, BookUpdate


class BookService:
    def __init__(self, repository: BookRepository) -> None:
        self._repo = repository

    def list_books(
        self,
        *,
        genre: str | None = None,
        search: str | None = None,
        available: bool | None = None,
        featured: bool | None = None,
    ) -> list[BookRead]:
        return self._repo.list_books(
            genre=genre,
            search=search,
            available=available,
            featured=featured,
        )

    def list_genres(self) -> list[str]:
        return self._repo.list_genres()

    def get_book(self, book_id: int) -> BookRead:
        book = self._repo.get(book_id)
        if book is None:
            raise NotFoundError("Book", book_id)
        return book

    def create_book(self, payload: BookCreate) -> BookRead:
        if payload.isbn is not None and self._repo.isbn_taken(payload.isbn):
            raise ConflictError("Another book already uses this ISBN")
        return self._repo.create(payload)

    def replace_book(self, book_id: int, payload: BookCreate) -> BookRead:
        if payload.isbn is not None and self._repo.isbn_taken(payload.isbn, except_id=book_id):
            raise ConflictError("Another book already uses this ISBN")
        book = self._repo.replace(book_id, payload)
        if book is None:
            raise NotFoundError("Book", book_id)
        return book

    def update_book(self, book_id: int, payload: BookUpdate) -> BookRead:
        changes = payload.model_dump(exclude_unset=True)
        if "isbn" in changes and changes["isbn"] not in (None, ""):
            isbn = str(changes["isbn"])
            if self._repo.isbn_taken(isbn, except_id=book_id):
                raise ConflictError("Another book already uses this ISBN")
        book = self._repo.update(book_id, payload)
        if book is None:
            raise NotFoundError("Book", book_id)
        return book

    def feature_book(self, book_id: int) -> BookRead:
        book = self._repo.set_featured(book_id, True)
        if book is None:
            raise NotFoundError("Book", book_id)
        return book

    def unfeature_book(self, book_id: int) -> BookRead:
        book = self._repo.set_featured(book_id, False)
        if book is None:
            raise NotFoundError("Book", book_id)
        return book

    def delete_book(self, book_id: int) -> BookRead:
        book = self._repo.delete(book_id)
        if book is None:
            raise NotFoundError("Book", book_id)
        return book
