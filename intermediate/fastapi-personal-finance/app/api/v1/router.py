from fastapi import APIRouter

from app.api.v1.endpoints import accounts, auth, health, spending, transactions, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(
    transactions.router,
    prefix="/accounts/{slug}/transactions",
    tags=["transactions"],
)
api_router.include_router(spending.router, prefix="/spending", tags=["spending"])
