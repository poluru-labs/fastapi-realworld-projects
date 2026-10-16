from app.repositories.bookmark_repository import BookmarkRepository
from app.schemas.bookmark import (
    BookmarkCreate,
    BookmarkDeleteResponse,
    BookmarkRead,
    BookmarkUpdate,
    TagListResponse,
)


class BookmarkService:
    def __init__(self, repo: BookmarkRepository) -> None:
        self._repo = repo

    def list_tags(self) -> TagListResponse:
        return TagListResponse(tags=self._repo.list_tags())

    def list_bookmarks(
        self,
        *,
        tag: str | None,
        search: str | None,
        pinned: bool | None,
        archived: bool,
    ) -> list[BookmarkRead]:
        rows = self._repo.list_bookmarks(
            tag=tag,
            search=search,
            pinned=pinned,
            archived=archived,
        )
        return [BookmarkRead.model_validate(r) for r in rows]

    def get_bookmark(self, bookmark_id: int) -> BookmarkRead:
        return BookmarkRead.model_validate(self._repo.get(bookmark_id))

    def create_bookmark(self, payload: BookmarkCreate) -> BookmarkRead:
        record = self._repo.create(
            title=payload.title,
            url=str(payload.url),
            tags=payload.tags,
            note=payload.note,
            pinned=payload.pinned,
        )
        return BookmarkRead.model_validate(record)

    def update_bookmark(self, bookmark_id: int, payload: BookmarkUpdate) -> BookmarkRead:
        record = self._repo.update(
            bookmark_id,
            title=payload.title,
            url=str(payload.url) if payload.url is not None else None,
            tags=payload.tags,
            note=payload.note,
            pinned=payload.pinned,
        )
        return BookmarkRead.model_validate(record)

    def pin(self, bookmark_id: int) -> BookmarkRead:
        return BookmarkRead.model_validate(self._repo.set_pinned(bookmark_id, pinned=True))

    def unpin(self, bookmark_id: int) -> BookmarkRead:
        return BookmarkRead.model_validate(self._repo.set_pinned(bookmark_id, pinned=False))

    def archive(self, bookmark_id: int) -> BookmarkRead:
        return BookmarkRead.model_validate(self._repo.set_archived(bookmark_id, archived=True))

    def unarchive(self, bookmark_id: int) -> BookmarkRead:
        return BookmarkRead.model_validate(self._repo.set_archived(bookmark_id, archived=False))

    def delete_bookmark(self, bookmark_id: int) -> BookmarkDeleteResponse:
        self._repo.delete(bookmark_id)
        return BookmarkDeleteResponse(id=bookmark_id)
