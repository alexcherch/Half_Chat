from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from half_chat.auth import get_current_user, hash_password, verify_password
from half_chat.database import engine
from half_chat.models import GroupBan, GroupMember, Message, User
from half_chat.schemas import PasswordUpdate, UserUpdate
from half_chat.ws import manager

router = APIRouter()


@router.get("/api/users", response_model=List[str])
def search_users(q: str = Query(default="", min_length=0)):
    with Session(engine) as session:
        statement = select(User.username)
        if q.strip():
            statement = statement.where(User.username.ilike(f"%{q.strip()}%"))  # type: ignore[attr-defined]
        statement = statement.order_by(User.username)  # type: ignore[attr-defined]
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
    return {"username": current_user.username, "date_of_birth": current_user.date_of_birth}


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

            for message in session.exec(  # type: ignore[union-attr]
                select(Message).where(Message.username == old_username)
            ).all():
                message.username = new_username

            for member in session.exec(  # type: ignore[union-attr]
                select(GroupMember).where(GroupMember.username == old_username)
            ).all():
                member.username = new_username

            for ban in session.exec(  # type: ignore[union-attr]
                select(GroupBan).where(GroupBan.username == old_username)
            ).all():
                ban.username = new_username

        if update_data.date_of_birth is not None:
            user.date_of_birth = update_data.date_of_birth.strip() or None

        session.add(user)
        session.commit()
        session.refresh(user)

    return {"username": user.username, "date_of_birth": user.date_of_birth}


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
