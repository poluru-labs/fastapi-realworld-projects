from functools import lru_cache

from app.repositories.recipe_repository import RecipeRepository
from app.services.recipe_service import RecipeService


@lru_cache
def get_recipe_repository() -> RecipeRepository:
    return RecipeRepository()


def get_recipe_service() -> RecipeService:
    return RecipeService(get_recipe_repository())
