from dataclasses import dataclass

from app.schemas.api_key import ApiKeyScope
from app.schemas.user import UserRead


@dataclass(frozen=True)
class Principal:
    user: UserRead
    auth_method: str
    api_key_id: int | None = None
    api_key_prefix: str | None = None
    scopes: tuple[ApiKeyScope, ...] = ()

    def has_scope(self, scope: ApiKeyScope) -> bool:
        if self.auth_method == "jwt":
            return True
        return scope in self.scopes
