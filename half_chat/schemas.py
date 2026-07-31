from typing import Optional

from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str
    date_of_birth: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageUpdate(BaseModel):
    text: str


class GroupCreate(BaseModel):
    name: str


class GroupRead(BaseModel):
    id: int
    name: str
    created_by: str
    created_at: str
    member_count: int = 0


class AddMember(BaseModel):
    username: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    date_of_birth: Optional[str] = None


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str
