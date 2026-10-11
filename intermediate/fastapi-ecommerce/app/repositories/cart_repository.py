from dataclasses import dataclass


@dataclass
class CartLineRecord:
    product_id: int
    quantity: int


class CartRepository:
    """One cart per user id. Lines keyed by product_id."""

    def __init__(self) -> None:
        self._carts: dict[int, dict[int, CartLineRecord]] = {}

    def lines_for_user(self, user_id: int) -> list[CartLineRecord]:
        cart = self._carts.get(user_id, {})
        return list(cart.values())

    def get_line(self, user_id: int, product_id: int) -> CartLineRecord | None:
        return self._carts.get(user_id, {}).get(product_id)

    def upsert_line(self, user_id: int, line: CartLineRecord) -> None:
        cart = self._carts.setdefault(user_id, {})
        cart[line.product_id] = line

    def remove_line(self, user_id: int, product_id: int) -> None:
        cart = self._carts.get(user_id)
        if cart is None:
            return
        cart.pop(product_id, None)
        if not cart:
            self._carts.pop(user_id, None)

    def clear(self, user_id: int) -> None:
        self._carts.pop(user_id, None)
