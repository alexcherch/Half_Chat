from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select

from half_chat.config import ACCESS_TOKEN_EXPIRE_DAYS, ALGORITHM, SECRET_KEY
from half_chat.database import engine
from half_chat.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)  # type: ignore[no-any-return]


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)  # type: ignore[no-any-return]


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)  # type: ignore[no-any-return]


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Необходима авторизация")

    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not isinstance(username, str):
            raise HTTPException(status_code=401, detail="Неверный токен")
    except JWTError:
        raise HTTPException(status_code=401, detail="Неверный токен")

    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if user is None:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        return user
