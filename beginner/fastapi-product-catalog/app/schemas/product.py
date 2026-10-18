from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


def _strip_text(value: object) -> object:
    if isinstance(value, str):
        return value.strip()
    return value


def _normalize_sku(value: str) -> str:
    return value.strip().upper()


def _normalize_tags(tags: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in tags:
        t = raw.strip().lower()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= 12:
            break
    return out


class ProductCreate(BaseModel):
    sku: str = Field(..., min_length=2, max_length=32, description="Unique stock-keeping unit.")
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    price: float = Field(..., ge=0, description="Unit price in your shop currency.")
    category: str = Field(..., min_length=1, max_length=64)
    tags: list[str] = Field(default_factory=list, max_length=12)
    stock_quantity: int = Field(default=0, ge=0)
    featured: bool = False

    @field_validator("sku", mode="before")
    @classmethod
    def normalize_sku(cls, value: object) -> object:
        if isinstance(value, str):
            return _normalize_sku(value)
        return value

    @field_validator("name", "description", "category", mode="before")
    @classmethod
    def strip_fields(cls, value: object) -> object:
        return _strip_text(value)

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            return []
        return _normalize_tags([str(v) for v in value])


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    price: float | None = Field(default=None, ge=0)
    category: str | None = Field(default=None, min_length=1, max_length=64)
    tags: list[str] | None = Field(default=None, max_length=12)
    stock_quantity: int | None = Field(default=None, ge=0)
    featured: bool | None = None

    @field_validator("name", "description", "category", mode="before")
    @classmethod
    def strip_fields(cls, value: object) -> object:
        return _strip_text(value)

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, list):
            return []
        return _normalize_tags([str(v) for v in value])


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    description: str
    price: float
    category: str
    tags: list[str]
    stock_quantity: int
    featured: bool
    discontinued: bool
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def in_stock(self) -> bool:
        return self.stock_quantity > 0


class ProductDeleteResponse(BaseModel):
    deleted: bool = True
    id: int


class CategoryListResponse(BaseModel):
    categories: list[str]
