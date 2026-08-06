import os
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlmodel import Session, select

from half_chat.auth import get_current_user, hash_password, verify_password
from half_chat.database import engine
from half_chat.models import GroupBan, GroupMember, Message, User
from half_chat.schemas import PasswordUpdate, UserUpdate
from half_chat.ws import manager

router = APIRouter()

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
AVATARS_DIR = os.path.join(STATIC_DIR, "avatars")
MAX_AVATAR_SIZE = 5 * 1024 * 1024
ALLOWED_AVATAR_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _is_valid_image(content: bytes, content_type: str) -> bool:
    if content_type == "image/png":
        return content[:8] == b"\x89PNG\r\n\x1a\n"
    if content_type == "image/jpeg":
        return content[:3] == b"\xff\xd8\xff"
    if content_type == "image/webp":
        return content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    if content_type == "image/gif":
        return content[:6] in (b"GIF87a", b"GIF89a")
    return False


@router.get("/api/users", response_model=List[str])
def search_users(q: str = Query(default="", min_length=0)):
    with Session(engine) as session:
        statement = select(User.username)
        if q.strip():
            statement = statement.where(User.username.ilike(f"%{q.strip()}%"))  # type: ignore[attr-defined]
        statement = statement.order_by(User.username)
        results = session.exec(statement).all()
        return results


@router.get("/api/users/{username}/status")
def get_user_status(username: str):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        return {"username": user.username, "online": manager.is_online(user.username)}


@router.get("/api/users/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "date_of_birth": current_user.date_of_birth,
        "avatar_url": current_user.avatar_url,
    }


@router.put("/api/users/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    ext = ALLOWED_AVATAR_TYPES.get(file.content_type or "")
    if not ext:
        raise HTTPException(
            status_code=400,
            detail="Поддерживаются только PNG, JPEG, WebP, GIF",
        )

    content = await file.read(MAX_AVATAR_SIZE + 1)
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=413, detail="Файл слишком большой (максимум 5 МБ)")

    if not _is_valid_image(content, file.content_type or ""):
        raise HTTPException(status_code=400, detail="Файл не является изображением")

    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == current_user.username)).first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        if user.avatar_url:
            old_path = os.path.join(AVATARS_DIR, os.path.basename(user.avatar_url))
            if os.path.isfile(old_path):
                os.remove(old_path)

        os.makedirs(AVATARS_DIR, exist_ok=True)
        filename = f"u{user.id}{ext}"
        with open(os.path.join(AVATARS_DIR, filename), "wb") as f:
            f.write(content)

        user.avatar_url = f"/static/avatars/{filename}"
        session.add(user)
        session.commit()
        session.refresh(user)

    return {
        "username": user.username,
        "date_of_birth": user.date_of_birth,
        "avatar_url": user.avatar_url,
    }


@router.put("/api/users/me")
def update_me(update_data: UserUpdate, current_user: User = Depends(get_current_user)):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == current_user.username)).first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        new_username = update_data.username.strip() if update_data.username else None
        if new_username and new_username != user.username:
            existing = session.exec(select(User).where(User.username == new_username)).first()
            if existing:
                raise HTTPException(status_code=400, detail="Пользователь уже существует")

            old_username = user.username
            user.username = new_username

            for message in session.exec(
                select(Message).where(Message.username == old_username)
            ).all():
                message.username = new_username

            for member in session.exec(
                select(GroupMember).where(GroupMember.username == old_username)
            ).all():
                member.username = new_username

            for ban in session.exec(
                select(GroupBan).where(GroupBan.username == old_username)
            ).all():
                ban.username = new_username

        if update_data.date_of_birth is not None:
            user.date_of_birth = update_data.date_of_birth.strip() or None

        session.add(user)
        session.commit()
        session.refresh(user)

    return {
        "username": user.username,
        "date_of_birth": user.date_of_birth,
        "avatar_url": user.avatar_url,
    }


@router.put("/api/users/me/password")
def update_password(password_data: PasswordUpdate, current_user: User = Depends(get_current_user)):
    if not password_data.new_password.strip():
        raise HTTPException(status_code=400, detail="Новый пароль не может быть пустым")

    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == current_user.username)).first()
        if not user or not verify_password(password_data.current_password, user.password_hash):
            raise HTTPException(status_code=400, detail="Неверный текущий пароль")

        user.password_hash = hash_password(password_data.new_password)
        session.add(user)
        session.commit()

    return {"status": "success"}
