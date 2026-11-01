from pydantic import BaseModel, ConfigDict, Field


class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., ge=0)
    in_stock: bool = True


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    price: float | None = Field(None, ge=0)
    in_stock: bool | None = None


class ItemRead(ItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class ItemDeleteResponse(BaseModel):
    deleted: bool = True
    item: ItemRead
