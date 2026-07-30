from typing import List

from fastapi import APIRouter, Query
from sqlmodel import Session, select

from half_chat.database import engine
from half_chat.models import User

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
