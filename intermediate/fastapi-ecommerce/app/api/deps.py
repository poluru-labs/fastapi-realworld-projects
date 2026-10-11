from collections.abc import Callable
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer

from app.core.config import Settings, get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.repositories.cart_repository import CartRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserRead, UserRole
from app.services.auth_service import AuthService
from app.services.cart_service import CartService
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@lru_cache
def get_user_repository() -> UserRepository:
    return UserRepository()


@lru_cache
def get_refresh_token_repository() -> RefreshTokenRepository:
    return RefreshTokenRepository()


@lru_cache
def get_product_repository() -> ProductRepository:
    return ProductRepository()


@lru_cache
def get_cart_repository() -> CartRepository:
    return CartRepository()


@lru_cache
def get_order_repository() -> OrderRepository:
    return OrderRepository()


def get_auth_service(
    settings: Annotated[Settings, Depends(get_settings)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    refresh_tokens: Annotated[RefreshTokenRepository, Depends(get_refresh_token_repository)],
) -> AuthService:
    return AuthService(settings=settings, users=users, refresh_tokens=refresh_tokens)


def get_user_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    return UserService(users)


def get_product_service(
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> ProductService:
    return ProductService(products=products, users=users)


def get_cart_service(
    carts: Annotated[CartRepository, Depends(get_cart_repository)],
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    product_service: Annotated[ProductService, Depends(get_product_service)],
) -> CartService:
    return CartService(carts=carts, products=products, product_service=product_service)


def get_order_service(
    orders: Annotated[OrderRepository, Depends(get_order_repository)],
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    carts: Annotated[CartRepository, Depends(get_cart_repository)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    cart_service: Annotated[CartService, Depends(get_cart_service)],
) -> OrderService:
    return OrderService(
        orders=orders,
        products=products,
        carts=carts,
        users=users,
        cart_service=cart_service,
    )


def _user_from_access_token(token: str, settings: Settings, users: UserRepository) -> UserRead:
    payload = decode_token(settings=settings, token=token, expected_type="access")
    user_id = int(payload["sub"])
    record = users.get_by_id(user_id)
    if record is None or not record.is_active:
        raise UnauthorizedError()
    return record.to_read()


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserRead:
    return _user_from_access_token(token, settings, users)


def get_optional_user(
    settings: Annotated[Settings, Depends(get_settings)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    authorization: Annotated[str | None, Header(include_in_schema=False)] = None,
) -> UserRead | None:
    if authorization is None:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedError()
    return _user_from_access_token(token, settings, users)


def require_roles(*allowed: UserRole) -> Callable[..., UserRead]:
    def checker(current_user: Annotated[UserRead, Depends(get_current_user)]) -> UserRead:
        if current_user.role not in allowed:
            raise ForbiddenError()
        return current_user

    return checker
