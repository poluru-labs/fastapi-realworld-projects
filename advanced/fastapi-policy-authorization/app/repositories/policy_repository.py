from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy import Document, PolicyRule, Role, User, UserRole


class PolicyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def email_exists(self, email: str) -> bool:
        result = await self._session.execute(select(User.id).where(User.email == email))
        return result.scalar_one_or_none() is not None

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> User | None:
        return await self._session.get(User, user_id)

    async def add_user(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        return user

    async def list_roles(self) -> list[Role]:
        result = await self._session.scalars(select(Role).order_by(Role.slug))
        return list(result)

    async def get_role_by_slug(self, slug: str) -> Role | None:
        result = await self._session.execute(select(Role).where(Role.slug == slug))
        return result.scalar_one_or_none()

    async def add_user_role(self, row: UserRole) -> UserRole:
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_user_roles(self, user_id: int) -> list[str]:
        result = await self._session.execute(
            select(Role.slug)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        return list(result.scalars())

    async def list_policies(self) -> list[PolicyRule]:
        stmt = select(PolicyRule).order_by(PolicyRule.priority.desc())
        result = await self._session.scalars(stmt)
        return list(result)

    async def policy_name_exists(self, name: str) -> bool:
        result = await self._session.execute(select(PolicyRule.id).where(PolicyRule.name == name))
        return result.scalar_one_or_none() is not None

    async def add_policy(self, rule: PolicyRule) -> PolicyRule:
        self._session.add(rule)
        await self._session.flush()
        return rule

    async def list_documents(self) -> list[Document]:
        result = await self._session.scalars(select(Document).order_by(Document.id.desc()))
        return list(result)

    async def get_document(self, document_id: int) -> Document | None:
        return await self._session.get(Document, document_id)

    async def add_document(self, document: Document) -> Document:
        self._session.add(document)
        await self._session.flush()
        return document
