from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from half_chat.auth import create_access_token, hash_password, verify_password
from half_chat.database import engine
from half_chat.models import User
from half_chat.schemas import Token, UserCreate

router = APIRouter()


@router.post("/register", status_code=201)
def register(user_data: UserCreate):
    if not user_data.username.strip() or not user_data.password.strip():
        raise HTTPException(
            status_code=400, detail="Имя и пароль не могут быть пустыми"
        )

    with Session(engine) as session:
        existing = session.exec(
            select(User).where(User.username == user_data.username.strip())
        ).first()
        if existing:
            raise HTTPException(
                status_code=400, detail="Пользователь уже существует"
            )

        user = User(
            username=user_data.username.strip(),
            password_hash=hash_password(user_data.password),
        )
        session.add(user)
        session.commit()
        return {"status": "success", "username": user.username}


@router.post("/login", response_model=Token)
def login(user_data: UserCreate):
    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.username == user_data.username.strip())
        ).first()
        if not user or not verify_password(user_data.password, user.password_hash):
            raise HTTPException(
                status_code=401, detail="Неверное имя пользователя или пароль"
            )

        access_token = create_access_token(data={"sub": user.username})
        return Token(access_token=access_token)
