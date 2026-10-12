from app.schemas.recipe import Difficulty, RecipeCreate, RecipeRead, RecipeUpdate


def _normalize_url(value: str) -> str:
    return value.strip().rstrip("/").casefold()


_SEED: dict[int, RecipeRead] = {
    1: RecipeRead(
        id=1,
        title="Weeknight Pasta",
        chef="Alex Rivera",
        source_url="https://example.com/weeknight-pasta",
        cuisine="Italian",
        prep_minutes=10,
        cook_minutes=15,
        total_minutes=25,
        servings=4,
        difficulty=Difficulty.EASY,
        vegetarian=True,
        steps="Boil pasta. Sauté garlic in olive oil. Toss and serve.",
        featured=True,
    ),
    2: RecipeRead(
        id=2,
        title="Classic Chili",
        chef="Jordan Lee",
        source_url=None,
        cuisine="American",
        prep_minutes=20,
        cook_minutes=60,
        total_minutes=80,
        servings=6,
        difficulty=Difficulty.MEDIUM,
        vegetarian=False,
        steps="Brown beef, simmer beans and spices for one hour.",
        featured=False,
    ),
    3: RecipeRead(
        id=3,
        title="Mushroom Risotto",
        chef="Sam Patel",
        source_url=None,
        cuisine="Italian",
        prep_minutes=15,
        cook_minutes=35,
        total_minutes=50,
        servings=4,
        difficulty=Difficulty.MEDIUM,
        vegetarian=True,
        steps="Toast rice, add stock gradually, finish with parmesan.",
        featured=False,
    ),
}


class RecipeRepository:
    """In-memory recipe box. Restarting the process restores the seed recipes."""

    def __init__(self) -> None:
        self._recipes = dict(_SEED)
        self._next_id = max(self._recipes.keys(), default=0) + 1

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
        items = list(self._recipes.values())
        if cuisine is not None:
            needle = cuisine.strip().casefold()
            if needle:
                items = [recipe for recipe in items if recipe.cuisine.casefold() == needle]
        if featured is not None:
            items = [recipe for recipe in items if recipe.featured is featured]
        if difficulty is not None:
            items = [recipe for recipe in items if recipe.difficulty is difficulty]
        if vegetarian is not None:
            items = [recipe for recipe in items if recipe.vegetarian is vegetarian]
        if max_total_minutes is not None:
            items = [
                recipe
                for recipe in items
                if recipe.total_minutes is not None
                and recipe.total_minutes <= max_total_minutes
            ]
        if search is not None:
            needle = search.strip().casefold()
            if needle:
                items = [
                    recipe
                    for recipe in items
                    if needle in recipe.title.casefold()
                    or needle in recipe.chef.casefold()
                    or needle in recipe.steps.casefold()
                    or (
                        recipe.source_url is not None
                        and needle in _normalize_url(recipe.source_url)
                    )
                ]
        return sorted(items, key=lambda recipe: (not recipe.featured, recipe.id))

    def list_cuisines(self) -> list[str]:
        cuisines = {recipe.cuisine for recipe in self._recipes.values()}
        return sorted(cuisines, key=str.casefold)

    def get(self, recipe_id: int) -> RecipeRead | None:
        return self._recipes.get(recipe_id)

    def source_url_taken(self, source_url: str, *, except_id: int | None = None) -> bool:
        normalized = _normalize_url(source_url)
        for recipe in self._recipes.values():
            if except_id is not None and recipe.id == except_id:
                continue
            if recipe.source_url is not None and _normalize_url(recipe.source_url) == normalized:
                return True
        return False

    def create(self, payload: RecipeCreate) -> RecipeRead:
        recipe = RecipeRead(
            id=self._next_id,
            title=payload.title,
            chef=payload.chef,
            source_url=payload.source_url,
            cuisine=payload.cuisine,
            prep_minutes=payload.prep_minutes,
            cook_minutes=payload.cook_minutes,
            total_minutes=None,
            servings=payload.servings,
            difficulty=payload.difficulty,
            vegetarian=payload.vegetarian,
            steps=payload.steps,
            featured=payload.featured,
        )
        self._recipes[self._next_id] = recipe
        self._next_id += 1
        return recipe

    def replace(self, recipe_id: int, payload: RecipeCreate) -> RecipeRead | None:
        if recipe_id not in self._recipes:
            return None
        recipe = RecipeRead(id=recipe_id, total_minutes=None, **payload.model_dump())
        self._recipes[recipe_id] = recipe
        return recipe

    def update(self, recipe_id: int, payload: RecipeUpdate) -> RecipeRead | None:
        existing = self._recipes.get(recipe_id)
        if existing is None:
            return None
        data = existing.model_dump()
        changes = payload.model_dump(exclude_unset=True)
        if "source_url" in changes:
            url_value = changes["source_url"]
            data["source_url"] = None if url_value is None else url_value
            del changes["source_url"]
        data.update(changes)
        recipe = RecipeRead(**data)
        self._recipes[recipe_id] = recipe
        return recipe

    def set_featured(self, recipe_id: int, featured: bool) -> RecipeRead | None:
        existing = self._recipes.get(recipe_id)
        if existing is None:
            return None
        recipe = existing.model_copy(update={"featured": featured})
        self._recipes[recipe_id] = recipe
        return recipe

    def delete(self, recipe_id: int) -> RecipeRead | None:
        return self._recipes.pop(recipe_id, None)
