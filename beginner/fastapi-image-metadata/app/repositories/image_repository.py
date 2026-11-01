from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from io import BytesIO

from PIL import Image


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _jpeg_bytes(*, width: int, height: int, color: tuple[int, int, int]) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def _png_bytes(*, width: int, height: int, color: tuple[int, int, int]) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, format="PNG")
    return buffer.getvalue()


@dataclass
class ImageRecord:
    id: int
    filename: str
    content_type: str
    format: str
    width: int
    height: int
    size_bytes: int
    caption: str
    tags: list[str]
    content: bytes
    uploaded_at: datetime = field(default_factory=_utcnow)


def _seed() -> dict[int, ImageRecord]:
    hero = _jpeg_bytes(width=1280, height=720, color=(70, 130, 180))
    icon = _png_bytes(width=64, height=64, color=(255, 140, 0))
    return {
        1: ImageRecord(
            id=1,
            filename="hero.jpg",
            content_type="image/jpeg",
            format="JPEG",
            width=1280,
            height=720,
            size_bytes=len(hero),
            caption="Wide hero banner from seed data.",
            tags=["hero", "seed"],
            content=hero,
            uploaded_at=datetime.fromisoformat("2026-02-01T10:00:00+00:00"),
        ),
        2: ImageRecord(
            id=2,
            filename="icon.png",
            content_type="image/png",
            format="PNG",
            width=64,
            height=64,
            size_bytes=len(icon),
            caption="Small square icon.",
            tags=["icon", "seed"],
            content=icon,
            uploaded_at=datetime.fromisoformat("2026-02-05T14:30:00+00:00"),
        ),
    }


class ImageRepository:
    """In-memory image store (bytes and metadata reset on restart)."""

    def __init__(self) -> None:
        self._images = _seed()
        self._next_id = max(self._images.keys(), default=0) + 1

    def list_images(self) -> list[ImageRecord]:
        return list(self._images.values())

    def get_image(self, image_id: int) -> ImageRecord | None:
        return self._images.get(image_id)

    def create_image(
        self,
        *,
        filename: str,
        content_type: str,
        image_format: str,
        width: int,
        height: int,
        content: bytes,
        caption: str,
        tags: list[str],
    ) -> ImageRecord:
        image_id = self._next_id
        self._next_id += 1
        record = ImageRecord(
            id=image_id,
            filename=filename,
            content_type=content_type,
            format=image_format,
            width=width,
            height=height,
            size_bytes=len(content),
            caption=caption,
            tags=tags,
            content=content,
        )
        self._images[image_id] = record
        return record

    def update_metadata(
        self,
        image_id: int,
        *,
        caption: str | None,
        tags: list[str] | None,
    ) -> ImageRecord | None:
        record = self._images.get(image_id)
        if record is None:
            return None
        if caption is not None:
            record.caption = caption
        if tags is not None:
            record.tags = tags
        return record

    def delete_image(self, image_id: int) -> ImageRecord | None:
        return self._images.pop(image_id, None)


@lru_cache
def get_image_repository() -> ImageRepository:
    return ImageRepository()
