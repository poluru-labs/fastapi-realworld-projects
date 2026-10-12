from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_recipe_service
from app.schemas.recipe import (
    Difficulty,
    RecipeCreate,
    RecipeDeleteResponse,
    RecipeRead,
    RecipeUpdate,
)
from app.services.recipe_service import RecipeService

router = APIRouter()

_CREATE_EXAMPLES = {
    "full": {
        "summary": "Recipe with source link",
        "description": "source_url must be unique when provided.",
        "value": {
            "title": "Sheet Pan Lemon Chicken",
            "chef": "Taylor Brooks",
            "source_url": "https://example.com/lemon-chicken",
            "cuisine": "Mediterranean",
            "prep_minutes": 15,
            "cook_minutes": 25,
            "servings": 4,
            "difficulty": "easy",
            "vegetarian": False,
            "steps": "Roast chicken and vegetables until golden.",
        },
    },
    "minimal": {
        "summary": "Title and chef only",
        "value": {
            "title": "Pantry Fried Rice",
            "chef": "House kitchen",
            "cuisine": "Asian",
        },
    },
}

_UPDATE_EXAMPLES = {
    "vegetarian": {
        "summary": "Mark as vegetarian",
        "value": {"vegetarian": True},
    },
    "clear_url": {
        "summary": "Remove source URL",
        "value": {"source_url": ""},
    },
}


@router.get(
    "/cuisines",
    response_model=list[str],
    summary="List distinct cuisines",
    description="Sorted alphabetically from recipes currently in the box.",
)
def list_cuisines(service: Annotated[RecipeService, Depends(get_recipe_service)]) -> list[str]:
    return service.list_cuisines()


@router.get(
    "",
    response_model=list[RecipeRead],
    summary="List recipes",
    description=(
        "Featured recipes appear first, then smaller ids. "
        "Filter with `cuisine`, `search`, `featured`, `difficulty`, `vegetarian`, "
        "and `max_total_minutes`."
    ),
)
def list_recipes(
    service: Annotated[RecipeService, Depends(get_recipe_service)],
    cuisine: Annotated[
        str | None,
        Query(description="Exact cuisine match (case insensitive)."),
    ] = None,
    search: Annotated[str | None, Query(description="Substring search.")] = None,
    featured: Annotated[bool | None, Query(description="Filter featured recipes.")] = None,
    difficulty: Annotated[Difficulty | None, Query(description="easy, medium, or hard.")] = None,
    vegetarian: Annotated[bool | None, Query(description="Filter vegetarian recipes.")] = None,
    max_total_minutes: Annotated[
        int | None,
        Query(ge=1, description="Include recipes whose prep+cook time is at or below this."),
    ] = None,
) -> list[RecipeRead]:
    return service.list_recipes(
        cuisine=cuisine,
        search=search,
        featured=featured,
        difficulty=difficulty,
        vegetarian=vegetarian,
        max_total_minutes=max_total_minutes,
    )


@router.get("/{recipe_id}", response_model=RecipeRead, summary="Get one recipe")
def get_recipe(
    recipe_id: int,
    service: Annotated[RecipeService, Depends(get_recipe_service)],
) -> RecipeRead:
    return service.get_recipe(recipe_id)


@router.post(
    "",
    response_model=RecipeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a recipe",
)
def create_recipe(
    service: Annotated[RecipeService, Depends(get_recipe_service)],
    payload: Annotated[RecipeCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
) -> RecipeRead:
    return service.create_recipe(payload)


@router.put("/{recipe_id}", response_model=RecipeRead, summary="Replace a recipe")
def replace_recipe(
    recipe_id: int,
    payload: RecipeCreate,
    service: Annotated[RecipeService, Depends(get_recipe_service)],
) -> RecipeRead:
    return service.replace_recipe(recipe_id, payload)


@router.patch(
    "/{recipe_id}",
    response_model=RecipeRead,
    summary="Partial update",
)
def update_recipe(
    recipe_id: int,
    service: Annotated[RecipeService, Depends(get_recipe_service)],
    payload: Annotated[RecipeUpdate, Body(openapi_examples=_UPDATE_EXAMPLES)],
) -> RecipeRead:
    return service.update_recipe(recipe_id, payload)


@router.post("/{recipe_id}/feature", response_model=RecipeRead, summary="Mark as featured")
def feature_recipe(
    recipe_id: int,
    service: Annotated[RecipeService, Depends(get_recipe_service)],
) -> RecipeRead:
    return service.feature_recipe(recipe_id)


@router.post("/{recipe_id}/unfeature", response_model=RecipeRead, summary="Remove featured flag")
def unfeature_recipe(
    recipe_id: int,
    service: Annotated[RecipeService, Depends(get_recipe_service)],
) -> RecipeRead:
    return service.unfeature_recipe(recipe_id)


@router.delete("/{recipe_id}", response_model=RecipeDeleteResponse, summary="Remove a recipe")
def delete_recipe(
    recipe_id: int,
    service: Annotated[RecipeService, Depends(get_recipe_service)],
) -> RecipeDeleteResponse:
    removed = service.delete_recipe(recipe_id)
    return RecipeDeleteResponse(recipe=removed)
