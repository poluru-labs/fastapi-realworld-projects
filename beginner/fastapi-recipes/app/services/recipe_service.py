from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.recipe_repository import RecipeRepository
from app.schemas.recipe import Difficulty, RecipeCreate, RecipeRead, RecipeUpdate


class RecipeService:
    def __init__(self, repository: RecipeRepository) -> None:
        self._repo = repository

    def list_recipes(
        self,
        *,
        cuisine: str | None = None,
        search: str | None = None,
        featured: bool | None = None,
        difficulty: Difficulty | None = None,
        vegetarian: bool | None = None,
        max_total_minutes: int | None = None,
    ) -> list[RecipeRead]:
        return self._repo.list_recipes(
            cuisine=cuisine,
            search=search,
            featured=featured,
            difficulty=difficulty,
            vegetarian=vegetarian,
            max_total_minutes=max_total_minutes,
        )

    def list_cuisines(self) -> list[str]:
        return self._repo.list_cuisines()

    def get_recipe(self, recipe_id: int) -> RecipeRead:
        recipe = self._repo.get(recipe_id)
        if recipe is None:
            raise NotFoundError("Recipe", recipe_id)
        return recipe

    def create_recipe(self, payload: RecipeCreate) -> RecipeRead:
        if payload.source_url is not None and self._repo.source_url_taken(payload.source_url):
            raise ConflictError("Another recipe already uses this source URL")
        return self._repo.create(payload)

    def replace_recipe(self, recipe_id: int, payload: RecipeCreate) -> RecipeRead:
        if payload.source_url is not None and self._repo.source_url_taken(
            payload.source_url, except_id=recipe_id
        ):
            raise ConflictError("Another recipe already uses this source URL")
        recipe = self._repo.replace(recipe_id, payload)
        if recipe is None:
            raise NotFoundError("Recipe", recipe_id)
        return recipe

    def update_recipe(self, recipe_id: int, payload: RecipeUpdate) -> RecipeRead:
        changes = payload.model_dump(exclude_unset=True)
        if "source_url" in changes and changes["source_url"] not in (None, ""):
            url = str(changes["source_url"])
            if self._repo.source_url_taken(url, except_id=recipe_id):
                raise ConflictError("Another recipe already uses this source URL")
        recipe = self._repo.update(recipe_id, payload)
        if recipe is None:
            raise NotFoundError("Recipe", recipe_id)
        return recipe

    def feature_recipe(self, recipe_id: int) -> RecipeRead:
        recipe = self._repo.set_featured(recipe_id, True)
        if recipe is None:
            raise NotFoundError("Recipe", recipe_id)
        return recipe

    def unfeature_recipe(self, recipe_id: int) -> RecipeRead:
        recipe = self._repo.set_featured(recipe_id, False)
        if recipe is None:
            raise NotFoundError("Recipe", recipe_id)
        return recipe

    def delete_recipe(self, recipe_id: int) -> RecipeRead:
        recipe = self._repo.delete(recipe_id)
        if recipe is None:
            raise NotFoundError("Recipe", recipe_id)
        return recipe
