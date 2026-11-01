from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from app.core.policy_engine import evaluate_policies
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.policy import Document, PolicyRule, User, UserRole
from app.repositories.policy_repository import PolicyRepository
from app.schemas.policy import (
    ClearanceLevel,
    DocumentCreate,
    DocumentRead,
    EvaluateRequest,
    EvaluateResponse,
    PolicyRuleCreate,
    PolicyRuleRead,
    RoleAssignment,
    RoleRead,
    TokenResponse,
    UserLogin,
    UserRead,
    UserRegister,
)


class PolicyService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repo = PolicyRepository(session)

    async def register(self, payload: UserRegister) -> UserRead:
        if await self._repo.email_exists(payload.email):
            raise ConflictError("Email already registered")
        user = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            clearance=ClearanceLevel.INTERNAL.value,
        )
        await self._repo.add_user(user)
        await self._session.commit()
        return await self._user_read(user.id)

    async def login(self, payload: UserLogin) -> TokenResponse:
        user = await self._repo.get_user_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise UnauthorizedError("Incorrect email or password")
        if not user.is_active:
            raise UnauthorizedError("Account is inactive")
        roles = await self._repo.get_user_roles(user.id)
        token = create_access_token(settings=self._settings, user_id=user.id, roles=roles)
        await self._session.commit()
        return TokenResponse(access_token=token, user=await self._user_read(user.id))

    async def list_roles(self) -> list[RoleRead]:
        rows = await self._repo.list_roles()
        return [RoleRead.model_validate(row) for row in rows]

    async def assign_role(self, payload: RoleAssignment) -> UserRead:
        user = await self._repo.get_user_by_email(payload.email)
        if user is None:
            raise NotFoundError("User", payload.email)
        role = await self._repo.get_role_by_slug(payload.role_slug)
        if role is None:
            raise NotFoundError("Role", payload.role_slug)
        await self._repo.add_user_role(UserRole(user_id=user.id, role_id=role.id))
        await self._session.commit()
        return await self._user_read(user.id)

    async def create_policy(self, payload: PolicyRuleCreate) -> PolicyRuleRead:
        if await self._repo.policy_name_exists(payload.name):
            raise ConflictError(f"Policy {payload.name!r} already exists")
        row = PolicyRule(
            name=payload.name,
            effect=payload.effect.value,
            actions=payload.actions,
            resources=payload.resources,
            roles=payload.roles,
            required_clearance=(
                payload.required_clearance.value if payload.required_clearance else None
            ),
            priority=payload.priority,
            description=payload.description,
        )
        await self._repo.add_policy(row)
        await self._session.commit()
        return PolicyRuleRead.model_validate(row)

    async def list_policies(self) -> list[PolicyRuleRead]:
        rows = await self._repo.list_policies()
        return [PolicyRuleRead.model_validate(row) for row in rows]

    async def evaluate(self, user_id: int, payload: EvaluateRequest) -> EvaluateResponse:
        user = await self._repo.get_user_by_id(user_id)
        if user is None:
            raise UnauthorizedError()
        allowed, matched = await self._decide(
            user=user,
            action=payload.action,
            resource=payload.resource,
            resource_attributes=payload.resource_attributes,
        )
        return EvaluateResponse(
            allowed=allowed,
            matched_rule=matched,
            action=payload.action,
            resource=payload.resource,
        )

    async def list_documents(self, user_id: int) -> list[DocumentRead]:
        rows = await self._repo.list_documents()
        visible: list[DocumentRead] = []
        user = await self._repo.get_user_by_id(user_id)
        if user is None:
            raise UnauthorizedError()
        for row in rows:
            allowed, _ = await self._decide(
                user=user,
                action="documents:read",
                resource=f"document/{row.id}",
                resource_attributes={"classification": row.classification},
            )
            if allowed:
                visible.append(DocumentRead.model_validate(row))
        return visible

    async def create_document(self, user_id: int, payload: DocumentCreate) -> DocumentRead:
        await self.ensure_allowed(
            user_id=user_id,
            action="documents:create",
            resource="document/*",
        )
        row = Document(
            owner_id=user_id,
            title=payload.title,
            classification=payload.classification.value,
            body=payload.body,
        )
        await self._repo.add_document(row)
        await self._session.commit()
        return DocumentRead.model_validate(row)

    async def get_document(self, user_id: int, document_id: int) -> DocumentRead:
        row = await self._repo.get_document(document_id)
        if row is None:
            raise NotFoundError("Document", document_id)
        user = await self._repo.get_user_by_id(user_id)
        if user is None:
            raise UnauthorizedError()
        await self.ensure_allowed(
            user_id=user_id,
            action="documents:read",
            resource=f"document/{document_id}",
            resource_attributes={"classification": row.classification},
        )
        return DocumentRead.model_validate(row)

    async def ensure_allowed(
        self,
        *,
        user_id: int,
        action: str,
        resource: str,
        resource_attributes: dict | None = None,
    ) -> None:
        user = await self._repo.get_user_by_id(user_id)
        if user is None:
            raise UnauthorizedError()
        allowed, matched = await self._decide(
            user=user,
            action=action,
            resource=resource,
            resource_attributes=resource_attributes or {},
        )
        if not allowed:
            detail = f"Denied by policy for {action} on {resource}"
            if matched:
                detail = f"{detail} (rule: {matched})"
            raise ForbiddenError(detail)

    async def _decide(
        self,
        *,
        user: User,
        action: str,
        resource: str,
        resource_attributes: dict,
    ) -> tuple[bool, str | None]:
        roles = set(await self._repo.get_user_roles(user.id))
        rules = [
            {
                "name": row.name,
                "effect": row.effect,
                "actions": row.actions,
                "resources": row.resources,
                "roles": row.roles,
                "required_clearance": row.required_clearance,
                "priority": row.priority,
            }
            for row in await self._repo.list_policies()
        ]
        return evaluate_policies(
            rules=rules,
            user_roles=roles,
            user_clearance=user.clearance,
            action=action,
            resource=resource,
            resource_attributes=resource_attributes,
        )

    async def _user_read(self, user_id: int) -> UserRead:
        user = await self._repo.get_user_by_id(user_id)
        if user is None:
            raise NotFoundError("User", user_id)
        roles = await self._repo.get_user_roles(user_id)
        return UserRead(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            clearance=ClearanceLevel(user.clearance),
            is_active=user.is_active,
            roles=roles,
            created_at=user.created_at,
        )
