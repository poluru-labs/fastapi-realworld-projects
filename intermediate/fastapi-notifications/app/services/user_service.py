from app.core.exceptions import NotFoundError
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserRead


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repo = repository

    def list_users(self) -> list[UserRead]:
        return self._repo.list_all()

    def get_user(self, user_id: int) -> UserRead:
        user = self._repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User", user_id)
        return user.to_read()
