import os

from fastapi import HTTPException, UploadFile

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
AVATARS_DIR = os.path.join(STATIC_DIR, "avatars")
MAX_AVATAR_SIZE = 5 * 1024 * 1024
ALLOWED_AVATAR_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def is_valid_image(content: bytes, content_type: str) -> bool:
    if content_type == "image/png":
        return content[:8] == b"\x89PNG\r\n\x1a\n"
    if content_type == "image/jpeg":
        return content[:3] == b"\xff\xd8\xff"
    if content_type == "image/webp":
        return content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    if content_type == "image/gif":
        return content[:6] in (b"GIF87a", b"GIF89a")
    return False


async def save_avatar(file: UploadFile, filename: str) -> str:
    ext = ALLOWED_AVATAR_TYPES.get(file.content_type or "")
    if not ext:
        raise HTTPException(status_code=400, detail="Поддерживаются только PNG, JPEG, WebP, GIF")

    content = await file.read(MAX_AVATAR_SIZE + 1)
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=413, detail="Файл слишком большой (максимум 5 МБ)")

    if not is_valid_image(content, file.content_type or ""):
        raise HTTPException(status_code=400, detail="Файл не является изображением")

    os.makedirs(AVATARS_DIR, exist_ok=True)
    url = f"/static/avatars/{filename}{ext}"
    with open(os.path.join(AVATARS_DIR, f"{filename}{ext}"), "wb") as f:
        f.write(content)
    return url


def delete_avatar(url):
    if not url:
        return
    path = os.path.join(AVATARS_DIR, os.path.basename(url))
    if os.path.isfile(path):
        os.remove(path)
