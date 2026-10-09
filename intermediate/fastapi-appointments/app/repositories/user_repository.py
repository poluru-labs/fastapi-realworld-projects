from dataclasses import dataclass

from app.core.security import hash_password
from app.schemas.user import UserCreate, UserRead, UserRole


@dataclass
class UserRecord:
    id: int
    email: str
    hashed_password: str
    full_name: str
    role: UserRole
    is_active: bool

    def to_read(self) -> UserRead:
        return UserRead(
            id=self.id,
            email=self.email,
            full_name=self.full_name,
            role=self.role,
            is_active=self.is_active,
        )


def _seed_users() -> dict[int, UserRecord]:
    admin_password = hash_password("AdminPass123!")
    return {
        1: UserRecord(
            id=1,
            email="admin@example.com",
            hashed_password=admin_password,
            full_name="Admin User",
            role=UserRole.ADMIN,
            is_active=True,
        ),
    }


class UserRepository:
    def __init__(self) -> None:
        self._by_id = dict(_seed_users())
        self._by_email = {user.email.lower(): user for user in self._by_id.values()}
        self._next_id = max(self._by_id.keys(), default=0) + 1

    def list_all(self) -> list[UserRead]:
        return [user.to_read() for user in self._by_id.values()]

    def get_by_id(self, user_id: int) -> UserRecord | None:
        return self._by_id.get(user_id)

    def get_by_email(self, email: str) -> UserRecord | None:
        return self._by_email.get(email.lower())

    def create(self, payload: UserCreate, *, role: UserRole = UserRole.USER) -> UserRead:
        record = UserRecord(
            id=self._next_id,
            email=payload.email.lower(),
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            role=role,
            is_active=True,
        )
        self._by_id[record.id] = record
        self._by_email[record.email] = record
        self._next_id += 1
        return record.to_read()

    def email_exists(self, email: str) -> bool:
        return email.lower() in self._by_email
