import asyncio
import io
import uuid
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

PRODUCTS_SUBDIR = "products"
RECEIPTS_SUBDIR = "receipts"

_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
_MAX_SIDE = 1600


class ImageError(Exception):
    """`code`: too_large | invalid | type"""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def upload_path(upload_dir: str, subdir: str, name: str) -> Path:
    return Path(upload_dir) / subdir / name


def new_image_name(ext: str = "jpg") -> str:
    return f"{uuid.uuid4().hex}.{ext}"


def resolve_path(upload_dir: str, relative: str) -> Path | None:
    """DB dagi nisbiy yo'lni diskdagi yo'lga aylantiradi; upload_dir dan chiqib ketsa None."""
    root = Path(upload_dir).resolve()
    path = (root / relative).resolve()
    if root not in path.parents or not path.is_file():
        return None
    return path


def _save_sync(data: bytes, upload_dir: str, subdir: str, max_mb: int) -> str:
    if len(data) > max_mb * 1024 * 1024:
        raise ImageError("too_large")
    try:
        img = Image.open(io.BytesIO(data))
        fmt = img.format or ""
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ImageError("invalid") from exc
    if fmt not in _FORMATS:
        raise ImageError("type")
    img = ImageOps.exif_transpose(img)
    img.thumbnail((_MAX_SIDE, _MAX_SIDE))
    if fmt == "JPEG" and img.mode != "RGB":
        img = img.convert("RGB")
    name = new_image_name(_FORMATS[fmt])
    path = upload_path(upload_dir, subdir, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "PNG":
        img.save(path, fmt, optimize=True)
    else:
        img.save(path, fmt, quality=82, optimize=True)
    return f"{subdir}/{name}"


async def save_image(data: bytes, upload_dir: str, subdir: str, max_mb: int = 5) -> str:
    """Rasmni tekshiradi, siqadi va diskka saqlaydi; DB uchun nisbiy yo'lni qaytaradi."""
    return await asyncio.to_thread(_save_sync, data, upload_dir, subdir, max_mb)
