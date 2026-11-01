from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.aggregator_repository import AggregatorRepository, SourceRecord
from app.schemas.source import SourceCreate, SourceRead, SourceUpdate
from app.schemas.user import UserRead, UserRole


class SourceService:
    def __init__(self, repository: AggregatorRepository) -> None:
        self._repo = repository

    def list_sources(self, actor: UserRead) -> list[SourceRead]:
        rows = self._repo.list_sources()
        if actor.role != UserRole.ADMIN:
            rows = [row for row in rows if row.owner_id == actor.id]
        rows.sort(key=lambda row: row.slug)
        return [self._read(row) for row in rows]

    def get_source(self, slug: str, actor: UserRead) -> SourceRead:
        record = self._require_visible_source(slug, actor)
        return self._read(record)

    def create_source(self, payload: SourceCreate, actor: UserRead) -> SourceRead:
        if self._repo.get_source_by_slug(payload.slug):
            raise ConflictError(f"Source slug {payload.slug!r} is already registered")
        record = self._repo.create_source(
            slug=payload.slug,
            display_name=payload.display_name,
            base_url=str(payload.base_url),
            mock_catalog=payload.mock_catalog,
            description=payload.description,
            owner_id=actor.id,
        )
        return self._read(record)

    def update_source(self, slug: str, payload: SourceUpdate, actor: UserRead) -> SourceRead:
        record = self._require_owned_source(slug, actor)
        fields = payload.model_dump(exclude_unset=True)
        if "base_url" in fields and fields["base_url"] is not None:
            fields["base_url"] = str(fields["base_url"])
        updated = self._repo.update_source(record.id, **fields)
        assert updated is not None
        return self._read(updated)

    def delete_source(self, slug: str, actor: UserRead) -> None:
        record = self._require_owned_source(slug, actor)
        if self._repo.delete_source(record.id) is None:
            raise NotFoundError("Source", slug)

    def _require_visible_source(self, slug: str, actor: UserRead) -> SourceRecord:
        record = self._repo.get_source_by_slug(slug)
        if record is None or (record.owner_id != actor.id and actor.role != UserRole.ADMIN):
            raise NotFoundError("Source", slug)
        return record

    def _require_owned_source(self, slug: str, actor: UserRead) -> SourceRecord:
        record = self._repo.get_source_by_slug(slug)
        if record is None or record.owner_id != actor.id:
            raise NotFoundError("Source", slug)
        return record

    @staticmethod
    def _read(record: SourceRecord) -> SourceRead:
        return SourceRead(
            id=record.id,
            slug=record.slug,
            display_name=record.display_name,
            base_url=record.base_url,
            mock_catalog=record.mock_catalog,
            description=record.description,
            is_active=record.is_active,
            owner_id=record.owner_id,
            created_at=record.created_at,
        )
