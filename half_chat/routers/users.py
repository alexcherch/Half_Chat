from typing import List

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session, select

from half_chat.database import engine
from half_chat.models import User
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
