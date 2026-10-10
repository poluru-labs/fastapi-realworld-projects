from app.schemas.book import BookCreate, BookRead, BookUpdate, _normalize_isbn

_SEED: dict[int, BookRead] = {
    1: BookRead(
        id=1,
        title="The Pragmatic Programmer",
        author="David Thomas, Andrew Hunt",
        isbn="978-0201616224",
        genre="Software",
        publication_year=1999,
        available=True,
        featured=True,
    ),
    2: BookRead(
        id=2,
        title="Clean Code",
        author="Robert C. Martin",
        isbn="978-0132350884",
        genre="Software",
        publication_year=2008,
        available=True,
        featured=False,
    ),
    3: BookRead(
        id=3,
        title="Dune",
        author="Frank Herbert",
        isbn=None,
        genre="Science Fiction",
        publication_year=1965,
        available=False,
        featured=False,
    ),
}


class BookRepository:
    """In-memory catalog. Restarting the process restores the seed books."""

    def __init__(self) -> None:
        self._books = dict(_SEED)
        self._next_id = max(self._books.keys(), default=0) + 1

    def list_books(
        self,
        *,
        genre: str | None = None,
        search: str | None = None,
        available: bool | None = None,
        featured: bool | None = None,
    ) -> list[BookRead]:
        items = list(self._books.values())
        if genre is not None:
            needle = genre.strip().casefold()
            if needle:
                items = [book for book in items if book.genre.casefold() == needle]
        if available is not None:
            items = [book for book in items if book.available is available]
        if featured is not None:
            items = [book for book in items if book.featured is featured]
        if search is not None:
            needle = search.strip().casefold()
            if needle:
                items = [
                    book
                    for book in items
                    if needle in book.title.casefold()
                    or needle in book.author.casefold()
                    or (
                        book.isbn is not None
                        and needle in _normalize_isbn(book.isbn).casefold()
                    )
                ]
        return sorted(items, key=lambda book: (not book.featured, book.id))

    def list_genres(self) -> list[str]:
        genres = {book.genre for book in self._books.values()}
        return sorted(genres, key=str.casefold)

    def get(self, book_id: int) -> BookRead | None:
        return self._books.get(book_id)

    def isbn_taken(self, isbn: str, *, except_id: int | None = None) -> bool:
        normalized = _normalize_isbn(isbn)
        for book in self._books.values():
            if except_id is not None and book.id == except_id:
                continue
            if book.isbn is not None and _normalize_isbn(book.isbn) == normalized:
                return True
        return False

    def create(self, payload: BookCreate) -> BookRead:
        book = BookRead(
            id=self._next_id,
            title=payload.title,
            author=payload.author,
            isbn=payload.isbn,
            genre=payload.genre,
            publication_year=payload.publication_year,
            available=payload.available,
            featured=payload.featured,
        )
        self._books[self._next_id] = book
        self._next_id += 1
        return book

    def replace(self, book_id: int, payload: BookCreate) -> BookRead | None:
        if book_id not in self._books:
            return None
        book = BookRead(id=book_id, **payload.model_dump())
        self._books[book_id] = book
        return book

    def update(self, book_id: int, payload: BookUpdate) -> BookRead | None:
        existing = self._books.get(book_id)
        if existing is None:
            return None
        data = existing.model_dump()
        changes = payload.model_dump(exclude_unset=True)
        if "isbn" in changes:
            isbn_value = changes["isbn"]
            data["isbn"] = None if isbn_value is None else isbn_value
            del changes["isbn"]
        data.update(changes)
        book = BookRead(**data)
        self._books[book_id] = book
        return book

    def set_featured(self, book_id: int, featured: bool) -> BookRead | None:
        existing = self._books.get(book_id)
        if existing is None:
            return None
        book = existing.model_copy(update={"featured": featured})
        self._books[book_id] = book
        return book

    def delete(self, book_id: int) -> BookRead | None:
        return self._books.pop(book_id, None)
