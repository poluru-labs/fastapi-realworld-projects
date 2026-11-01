from datetime import UTC, datetime

from app.core.config import Settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import hash_api_key
from app.repositories.key_repository import KeyRepository, ProjectRecord
from app.repositories.user_repository import UserRepository
from app.schemas.access import MetricsRead, WhoamiRead
from app.schemas.api_key import ApiKeyScope
from app.schemas.project import ProjectCreate, ProjectRead
from app.services.principal import Principal


class AccessService:
    def __init__(
        self,
        repository: KeyRepository,
        users: UserRepository,
        settings: Settings,
    ) -> None:
        self._repo = repository
        self._users = users
        self._settings = settings

    def resolve_api_key(self, raw_key: str) -> Principal:
        digest = hash_api_key(raw_key, self._settings.api_key_pepper)
        record = self._repo.get_key_by_hash(digest)
        if record is None:
            raise UnauthorizedError("Invalid X-Api-Key")
        if record.revoked_at is not None:
            raise UnauthorizedError("API key has been revoked")
        record.last_used_at = datetime.now(UTC)
        self._repo.save_key(record)
        user = self._users.get_by_id(record.owner_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("API key owner is inactive")
        return Principal(
            user=user.to_read(),
            auth_method="api_key",
            api_key_id=record.id,
            api_key_prefix=record.prefix,
            scopes=tuple(record.scopes),
        )

    def whoami(self, principal: Principal) -> WhoamiRead:
        return WhoamiRead(
            auth_method=principal.auth_method,
            user_id=principal.user.id,
            email=principal.user.email,
            api_key_id=principal.api_key_id,
            api_key_prefix=principal.api_key_prefix,
            scopes=list(principal.scopes),
        )

    def list_projects(self, principal: Principal) -> list[ProjectRead]:
        self._require_scope(principal, ApiKeyScope.PROJECTS_READ)
        rows = self._repo.list_projects_for_owner(principal.user.id)
        rows.sort(key=lambda row: row.name.casefold())
        return [self._project_read(row) for row in rows]

    def create_project(self, principal: Principal, payload: ProjectCreate) -> ProjectRead:
        self._require_scope(principal, ApiKeyScope.PROJECTS_WRITE)
        now = datetime.now(UTC)
        record = ProjectRecord(
            id=self._repo.allocate_project_id(),
            owner_id=principal.user.id,
            name=payload.name,
            description=payload.description,
            created_at=now,
        )
        self._repo.add_project(record)
        return self._project_read(record)

    def metrics(self, principal: Principal) -> MetricsRead:
        self._require_scope(principal, ApiKeyScope.METRICS_READ)
        return MetricsRead(
            project_count=len(self._repo.list_projects_for_owner(principal.user.id)),
            active_api_keys=self._repo.count_active_keys_for_owner(principal.user.id),
        )

    @staticmethod
    def _require_scope(principal: Principal, scope: ApiKeyScope) -> None:
        if not principal.has_scope(scope):
            raise ForbiddenError(f"API key requires scope {scope.value}")

    @staticmethod
    def _project_read(record: ProjectRecord) -> ProjectRead:
        return ProjectRead(
            id=record.id,
            name=record.name,
            description=record.description,
            owner_id=record.owner_id,
            created_at=record.created_at,
        )
