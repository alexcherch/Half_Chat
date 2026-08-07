from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlmodel import Session, select

from nedochat.auth import get_current_user, hash_password, verify_password
from nedochat.avatars import delete_avatar, save_avatar
from nedochat.database import engine
from nedochat.models import GroupBan, GroupMember, Message, User
from nedochat.schemas import PasswordUpdate, UserSearchRead, UserUpdate
from nedochat.ws import manager

router = APIRouter()


@router.get("/api/users", response_model=List[UserSearchRead])
def search_users(q: str = Query(default="", min_length=0)):
    with Session(engine) as session:
        statement = select(User)
        if q.strip():
            statement = statement.where(User.username.ilike(f"%{q.strip()}%"))  # type: ignore[attr-defined]
        statement = statement.order_by(User.username)
        results = session.exec(statement).all()
        return [
            UserSearchRead(username=user.username, display_name=user.display_name)
            for user in results
        ]


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
        "display_name": current_user.display_name,
        "date_of_birth": current_user.date_of_birth,
        "avatar_url": current_user.avatar_url,
    }


@router.put("/api/users/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == current_user.username)).first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        new_url = await save_avatar(file, f"u{user.id}")
        if user.avatar_url and user.avatar_url != new_url:
            delete_avatar(user.avatar_url)

        user.avatar_url = new_url
        session.add(user)
        session.commit()
        session.refresh(user)

    return {
        "username": user.username,
        "display_name": user.display_name,
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

        if update_data.display_name is not None:
            user.display_name = update_data.display_name.strip() or None

        session.add(user)
        session.commit()
        session.refresh(user)

    return {
        "username": user.username,
        "display_name": user.display_name,
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
