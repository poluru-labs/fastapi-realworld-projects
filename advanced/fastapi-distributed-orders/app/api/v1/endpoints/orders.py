from fastapi import APIRouter, Body, status

from app.api.deps import CurrentUser, DbSession, IdempotencyKey
from app.schemas.order import OrderCreate, OrderRead, OrderTransition
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])

_CREATE_EXAMPLES = {
    "widget": {
        "summary": "Single line order",
        "value": {"items": [{"sku": "WIDGET-1", "quantity": 2}]},
    }
}


@router.get(
    "",
    response_model=list[OrderRead],
    summary="List orders",
    description="Shoppers see their own orders. Admins see the full ledger.",
)
async def list_orders(actor: CurrentUser, session: DbSession) -> list[OrderRead]:
    return await OrderService(session).list_orders(actor)


@router.get("/{order_id}", response_model=OrderRead, summary="Get one order")
async def get_order(order_id: int, actor: CurrentUser, session: DbSession) -> OrderRead:
    return await OrderService(session).get_order(actor, order_id)


@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Place an order (idempotent)",
    description=(
        "Requires **`Idempotency-Key`** header. Retries with the same key return the original "
        "order body. Reserves inventory and appends an **`order.created`** outbox row in one "
        "transaction. **`X-Request-ID`** is stored as `correlation_id`."
    ),
)
async def create_order(
    actor: CurrentUser,
    session: DbSession,
    idempotency_key: IdempotencyKey,
    payload: OrderCreate = Body(openapi_examples=_CREATE_EXAMPLES),
) -> OrderRead:
    return await OrderService(session).create_order(
        actor,
        payload,
        idempotency_key=idempotency_key,
    )


@router.post("/{order_id}/pay", response_model=OrderRead, summary="Mark order paid")
async def pay_order(
    order_id: int,
    actor: CurrentUser,
    session: DbSession,
    body: OrderTransition,
) -> OrderRead:
    return await OrderService(session).pay(
        actor,
        order_id,
        expected_version=body.expected_version,
    )


@router.post("/{order_id}/fulfill", response_model=OrderRead, summary="Mark order fulfilled")
async def fulfill_order(
    order_id: int,
    actor: CurrentUser,
    session: DbSession,
    body: OrderTransition,
) -> OrderRead:
    return await OrderService(session).fulfill(
        actor,
        order_id,
        expected_version=body.expected_version,
    )


@router.post("/{order_id}/cancel", response_model=OrderRead, summary="Cancel and release stock")
async def cancel_order(
    order_id: int,
    actor: CurrentUser,
    session: DbSession,
    body: OrderTransition,
) -> OrderRead:
    return await OrderService(session).cancel(
        actor,
        order_id,
        expected_version=body.expected_version,
    )
