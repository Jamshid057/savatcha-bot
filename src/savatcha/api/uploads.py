from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse

from savatcha.core.config import Settings
from savatcha.core.services.files import ImageError, resolve_path, save_image


async def store_upload(file: UploadFile, settings: Settings, subdir: str) -> str:
    """Yuklangan rasmni tekshirib, siqib saqlaydi; ImageError -> 400."""
    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    try:
        return await save_image(data, settings.upload_dir, subdir, settings.max_upload_mb)
    except ImageError as exc:
        raise HTTPException(400, f"image_{exc.code}") from exc


def file_response(settings: Settings, relative_path: str | None) -> FileResponse:
    path = resolve_path(settings.upload_dir, relative_path) if relative_path else None
    if path is None:
        raise HTTPException(404, "not_found")
    return FileResponse(path, headers={"Cache-Control": "private, max-age=3600"})
