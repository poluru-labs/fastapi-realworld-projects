"""Cart line rules and stock checks before checkout live here."""

from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.cart_repository import CartLineRecord, CartRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.cart import CartLineRead, CartLineUpsert, CartRead
from app.schemas.product import ProductStatus
from app.schemas.user import UserRead
from app.services.product_service import ProductService


class CartService:
    def __init__(
        self,
        *,
        carts: CartRepository,
        products: ProductRepository,
        product_service: ProductService,
    ) -> None:
        self._carts = carts
        self._products = products
        self._products_svc = product_service

    def get_cart(self, actor: UserRead) -> CartRead:
        return self._build_cart(actor.id)

    def upsert_line(self, actor: UserRead, payload: CartLineUpsert) -> CartRead:
        product = self._products_svc.purchasable_record(payload.product_slug)
        if payload.quantity > product.stock:
            raise ConflictError("Requested quantity exceeds available stock")
        self._carts.upsert_line(
            actor.id,
            CartLineRecord(product_id=product.id, quantity=payload.quantity),
        )
        return self._build_cart(actor.id)

    def remove_line(self, actor: UserRead, product_slug: str) -> CartRead:
        product = self._products.get_by_slug(product_slug)
        if product is None:
            raise NotFoundError("Product", product_slug)
        self._carts.remove_line(actor.id, product.id)
        return self._build_cart(actor.id)

    def clear(self, actor: UserRead) -> CartRead:
        self._carts.clear(actor.id)
        return self._build_cart(actor.id)

    def _build_cart(self, user_id: int) -> CartRead:
        items: list[CartLineRead] = []
        subtotal = 0
        item_count = 0
        stale_product_ids: list[int] = []

        for line in self._carts.lines_for_user(user_id):
            product = self._products.get(line.product_id)
            if product is None or product.status is not ProductStatus.ACTIVE:
                stale_product_ids.append(line.product_id)
                continue
            if line.quantity > product.stock:
                line = CartLineRecord(product_id=line.product_id, quantity=product.stock)
                if line.quantity == 0:
                    stale_product_ids.append(product.id)
                    continue
                self._carts.upsert_line(user_id, line)
            line_total = line.quantity * product.price_cents
            subtotal += line_total
            item_count += line.quantity
            items.append(
                CartLineRead(
                    product_id=product.id,
                    product_slug=product.slug,
                    product_name=product.name,
                    quantity=line.quantity,
                    unit_price_cents=product.price_cents,
                    line_total_cents=line_total,
                )
            )

        for product_id in stale_product_ids:
            self._carts.remove_line(user_id, product_id)

        items.sort(key=lambda row: row.product_slug)
        return CartRead(items=items, item_count=item_count, subtotal_cents=subtotal)
