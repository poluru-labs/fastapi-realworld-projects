from app.core.exceptions import ConflictError, GoneError, NotFoundError
from app.repositories.link_repository import LinkRepository
from app.schemas.link import LinkCreate, LinkRead, LinkUpdate


class LinkService:
    def __init__(self, repository: LinkRepository) -> None:
        self._repo = repository

    def list_links(
        self,
        *,
        is_active: bool | None,
        q: str | None,
    ) -> list[LinkRead]:
        rows = self._repo.list_links()
        if is_active is not None:
            rows = [link for link in rows if link.is_active is is_active]
        if q:
            needle = q.casefold()
            rows = [
                link
                for link in rows
                if needle in link.code.casefold()
                or needle in link.title.casefold()
                or needle in link.target_url.casefold()
            ]
        rows.sort(key=lambda link: link.created_at, reverse=True)
        return [self._read(link) for link in rows]

    def get_link(self, code: str) -> LinkRead:
        return self._read(self._require_link(code))

    def create_link(self, payload: LinkCreate) -> LinkRead:
        code = payload.custom_code or self._allocate_code()
        if self._repo.code_exists(code):
            raise ConflictError(f"Short code {code!r} is already taken")
        record = self._repo.create_link(
            code=code,
            target_url=str(payload.target_url),
            title=payload.title,
        )
        return self._read(record)

    def update_link(self, code: str, payload: LinkUpdate) -> LinkRead:
        fields = payload.model_dump(exclude_unset=True)
        target = str(fields["target_url"]) if fields.get("target_url") is not None else None
        record = self._repo.update_link(
            code,
            target_url=target,
            title=fields.get("title"),
            is_active=fields.get("is_active"),
        )
        if record is None:
            raise NotFoundError("Link", code)
        return self._read(record)

    def delete_link(self, code: str) -> None:
        if self._repo.delete_link(code) is None:
            raise NotFoundError("Link", code)

    def resolve_redirect(self, code: str) -> str:
        record = self._require_link(code)
        if not record.is_active:
            raise GoneError("This short link is no longer active")
        updated = self._repo.record_click(code)
        assert updated is not None
        return updated.target_url

    def _allocate_code(self) -> str:
        for _ in range(10):
            code = self._repo.generate_code()
            if not self._repo.code_exists(code):
                return code
        raise ConflictError("Could not allocate a unique short code")

    def _require_link(self, code: str):
        record = self._repo.get_by_code(code)
        if record is None:
            raise NotFoundError("Link", code)
        return record

    @staticmethod
    def _read(link) -> LinkRead:
        return LinkRead(
            id=link.id,
            code=link.code,
            target_url=link.target_url,
            title=link.title,
            click_count=link.click_count,
            is_active=link.is_active,
            redirect_path=f"/api/v1/r/{link.code}",
            created_at=link.created_at,
        )
