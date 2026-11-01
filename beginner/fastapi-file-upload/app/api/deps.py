from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.repositories.file_repository import FileRepository, get_file_repository
from app.services.file_service import FileService


def get_file_service(
    repository: Annotated[FileRepository, Depends(get_file_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileService:
    return FileService(repository, settings)
