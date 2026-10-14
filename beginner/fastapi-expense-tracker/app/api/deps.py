from functools import lru_cache

from app.repositories.expense_repository import ExpenseRepository
from app.services.expense_service import ExpenseService


@lru_cache
def get_expense_repository() -> ExpenseRepository:
    return ExpenseRepository()


def get_expense_service() -> ExpenseService:
    return ExpenseService(get_expense_repository())
