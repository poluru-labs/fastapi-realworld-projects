import hashlib
from datetime import UTC, datetime

from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.repositories.flag_repository import FlagRecord, FlagRepository
from app.schemas.evaluate import EvaluateContext, EvaluateRequest, EvaluateResponse, FlagEvaluation
from app.schemas.flag import FlagCreate, FlagRead, FlagUpdate
from app.schemas.user import UserRead, UserRole


class FlagService:
    def __init__(self, repository: FlagRepository) -> None:
        self._repo = repository

    def list_flags(
        self,
        actor: UserRead,
        *,
        environment: str | None,
    ) -> list[FlagRead]:
        rows = self._repo.list_flags()
        if actor.role is not UserRole.ADMIN:
            rows = [row for row in rows if row.owner_id == actor.id]
        if environment is not None:
            needle = environment.casefold()
            rows = [row for row in rows if row.environment.value == needle]
        rows.sort(key=lambda row: row.key)
        return [self._read(row) for row in rows]

    def get_flag(self, actor: UserRead, key: str) -> FlagRead:
        return self._read(self._visible_flag(actor, key))

    def create_flag(self, actor: UserRead, payload: FlagCreate) -> FlagRead:
        if self._repo.key_taken(payload.key):
            raise ConflictError(f"Flag key {payload.key!r} is already defined")
        now = datetime.now(UTC)
        record = FlagRecord(
            id=self._repo.allocate_id(),
            key=payload.key,
            name=payload.name,
            description=payload.description,
            environment=payload.environment,
            enabled=payload.enabled,
            rollout_percentage=payload.rollout_percentage,
            allowlist_user_ids=list(payload.allowlist_user_ids),
            owner_id=actor.id,
            created_at=now,
            updated_at=now,
        )
        self._repo.add_flag(record)
        return self._read(record)

    def update_flag(self, actor: UserRead, key: str, payload: FlagUpdate) -> FlagRead:
        record = self._owned_flag(actor, key)
        changes = payload.model_dump(exclude_unset=True)
        if "name" in changes and changes["name"] is not None:
            record.name = changes["name"]
        if "description" in changes and changes["description"] is not None:
            record.description = changes["description"]
        if "environment" in changes and changes["environment"] is not None:
            record.environment = changes["environment"]
        if "enabled" in changes and changes["enabled"] is not None:
            record.enabled = changes["enabled"]
        if "rollout_percentage" in changes and changes["rollout_percentage"] is not None:
            record.rollout_percentage = changes["rollout_percentage"]
        if "allowlist_user_ids" in changes and changes["allowlist_user_ids"] is not None:
            record.allowlist_user_ids = list(changes["allowlist_user_ids"])
        record.updated_at = datetime.now(UTC)
        self._repo.save_flag(record)
        return self._read(record)

    def delete_flag(self, actor: UserRead, key: str) -> None:
        record = self._owned_flag(actor, key)
        self._repo.delete_flag(record.id)

    def evaluate(
        self,
        *,
        runtime_token: str,
        payload: EvaluateRequest,
    ) -> EvaluateResponse:
        token_record = self._repo.resolve_runtime_token(runtime_token)
        if token_record is None:
            raise UnauthorizedError("Invalid X-Runtime-Token")

        evaluations: list[FlagEvaluation] = []
        for flag_key in payload.flag_keys:
            record = self._repo.get_flag_by_key(flag_key)
            if record is None or record.owner_id != token_record.owner_id:
                evaluations.append(
                    FlagEvaluation(key=flag_key, enabled=False, reason="flag not found")
                )
                continue
            enabled, reason = self._evaluate_flag(record, payload.context)
            evaluations.append(FlagEvaluation(key=flag_key, enabled=enabled, reason=reason))

        return EvaluateResponse(evaluations=evaluations)

    def _evaluate_flag(
        self,
        record: FlagRecord,
        context: EvaluateContext,
    ) -> tuple[bool, str]:
        if not record.enabled:
            return False, "flag disabled"
        if context.user_id in record.allowlist_user_ids:
            return True, "allowlisted user"
        if record.rollout_percentage >= 100:
            return True, "full rollout"
        if record.rollout_percentage <= 0:
            return False, "zero rollout"
        if self._in_rollout(context.user_id, record.key, record.rollout_percentage):
            return True, "within rollout percentage"
        return False, "outside rollout percentage"

    @staticmethod
    def _in_rollout(user_id: str, flag_key: str, percentage: int) -> bool:
        digest = hashlib.sha256(f"{flag_key}:{user_id}".encode()).hexdigest()
        bucket = int(digest[:8], 16) % 100
        return bucket < percentage

    def _visible_flag(self, actor: UserRead, key: str) -> FlagRecord:
        record = self._repo.get_flag_by_key(key)
        if record is None or (record.owner_id != actor.id and actor.role is not UserRole.ADMIN):
            raise NotFoundError("Flag", key)
        return record

    def _owned_flag(self, actor: UserRead, key: str) -> FlagRecord:
        record = self._repo.get_flag_by_key(key)
        if record is None or record.owner_id != actor.id:
            raise NotFoundError("Flag", key)
        return record

    @staticmethod
    def _read(record: FlagRecord) -> FlagRead:
        return FlagRead(
            id=record.id,
            key=record.key,
            name=record.name,
            description=record.description,
            environment=record.environment,
            enabled=record.enabled,
            rollout_percentage=record.rollout_percentage,
            allowlist_user_ids=list(record.allowlist_user_ids),
            owner_id=record.owner_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
