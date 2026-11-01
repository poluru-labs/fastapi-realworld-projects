from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.repositories.image_repository import ImageRepository, get_image_repository
from app.services.image_service import ImageService


def get_image_service(
    repository: Annotated[ImageRepository, Depends(get_image_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ImageService:
    return ImageService(repository, settings)
