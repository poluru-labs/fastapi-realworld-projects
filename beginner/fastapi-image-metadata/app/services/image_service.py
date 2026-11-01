from io import BytesIO

from PIL import Image, UnidentifiedImageError

from app.core.config import Settings
from app.core.exceptions import AppError, NotFoundError, PayloadTooLargeError
from app.repositories.image_repository import ImageRepository
from app.schemas.image import ImageRead, ImageUpdate

ALLOWED_FORMATS = frozenset({"JPEG", "PNG", "WEBP", "GIF"})


class ImageService:
    def __init__(self, repository: ImageRepository, settings: Settings) -> None:
        self._repo = repository
        self._settings = settings

    def list_images(
        self,
        *,
        image_format: str | None,
        min_width: int | None,
        min_height: int | None,
        q: str | None,
    ) -> list[ImageRead]:
        rows = self._repo.list_images()
        if image_format:
            needle = image_format.casefold()
            rows = [row for row in rows if row.format.casefold() == needle]
        if min_width is not None:
            rows = [row for row in rows if row.width >= min_width]
        if min_height is not None:
            rows = [row for row in rows if row.height >= min_height]
        if q:
            needle = q.casefold()
            rows = [
                row
                for row in rows
                if needle in row.filename.casefold()
                or needle in row.caption.casefold()
                or any(needle in tag.casefold() for tag in row.tags)
            ]
        rows.sort(key=lambda row: row.uploaded_at, reverse=True)
        return [self._read(row) for row in rows]

    def get_image(self, image_id: int) -> ImageRead:
        return self._read(self._require_image(image_id))

    def get_content(self, image_id: int) -> tuple[bytes, str, str]:
        record = self._require_image(image_id)
        return record.content, record.content_type, record.filename

    async def upload_image(
        self,
        *,
        filename: str,
        content_type: str | None,
        content: bytes,
        caption: str,
        tags: list[str],
    ) -> ImageRead:
        if not filename.strip():
            raise AppError("filename is required")
        if len(content) == 0:
            raise AppError("image must not be empty")
        if len(content) > self._settings.max_upload_bytes:
            raise PayloadTooLargeError(
                f"Maximum upload size is {self._settings.max_upload_bytes} bytes"
            )

        image_format, width, height = self._inspect_image(content)
        safe_name = filename.split("/")[-1].split("\\")[-1]
        resolved_type = content_type or self._content_type_for_format(image_format)

        record = self._repo.create_image(
            filename=safe_name,
            content_type=resolved_type,
            image_format=image_format,
            width=width,
            height=height,
            content=content,
            caption=caption,
            tags=tags,
        )
        return self._read(record)

    def update_image(self, image_id: int, payload: ImageUpdate) -> ImageRead:
        fields = payload.model_dump(exclude_unset=True)
        if not fields:
            return self.get_image(image_id)
        record = self._repo.update_metadata(
            image_id,
            caption=fields.get("caption"),
            tags=fields.get("tags"),
        )
        if record is None:
            raise NotFoundError("Image", image_id)
        return self._read(record)

    def delete_image(self, image_id: int) -> None:
        if self._repo.delete_image(image_id) is None:
            raise NotFoundError("Image", image_id)

    def _require_image(self, image_id: int):
        record = self._repo.get_image(image_id)
        if record is None:
            raise NotFoundError("Image", image_id)
        return record

    @staticmethod
    def _inspect_image(content: bytes) -> tuple[str, int, int]:
        try:
            with Image.open(BytesIO(content)) as image:
                image_format = (image.format or "").upper()
                if image_format not in ALLOWED_FORMATS:
                    raise AppError(
                        f"Unsupported image format {image_format or 'unknown'}; "
                        f"use one of {', '.join(sorted(ALLOWED_FORMATS))}"
                    )
                width, height = image.size
        except UnidentifiedImageError as exc:
            raise AppError("Uploaded file is not a recognizable image") from exc
        return image_format, width, height

    @staticmethod
    def _content_type_for_format(image_format: str) -> str:
        mapping = {
            "JPEG": "image/jpeg",
            "PNG": "image/png",
            "WEBP": "image/webp",
            "GIF": "image/gif",
        }
        return mapping.get(image_format, "application/octet-stream")

    @staticmethod
    def _read(record) -> ImageRead:
        return ImageRead(
            id=record.id,
            filename=record.filename,
            content_type=record.content_type,
            format=record.format,
            width=record.width,
            height=record.height,
            size_bytes=record.size_bytes,
            caption=record.caption,
            tags=record.tags,
            content_path=f"/api/v1/images/{record.id}/content",
            uploaded_at=record.uploaded_at,
        )
