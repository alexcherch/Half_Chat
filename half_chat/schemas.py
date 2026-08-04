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
    is_direct: bool = False


class DirectCreate(BaseModel):
    username: str


class DirectRead(BaseModel):
    id: int
    peer: str
    created_at: str


class AddMember(BaseModel):
    username: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    date_of_birth: Optional[str] = None


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str
