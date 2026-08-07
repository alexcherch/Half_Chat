from typing import List, Optional

from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: Optional[str] = None
    date_of_birth: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageUpdate(BaseModel):
    text: str


class ForwardCreate(BaseModel):
    group_id: int


class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class GroupRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    created_by: str
    created_at: str
    member_count: int = 0
    is_direct: bool = False
    pinned_message_id: Optional[int] = None


class DirectCreate(BaseModel):
    username: str


class DirectRead(BaseModel):
    id: int
    peer: str
    created_at: str


class AddMember(BaseModel):
    username: str


class MemberRead(BaseModel):
    username: str
    role: str
    muted: bool = False
    display_name: Optional[str] = None


class UserSearchRead(BaseModel):
    username: str
    display_name: Optional[str] = None


class RoleUpdate(BaseModel):
    role: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    display_name: Optional[str] = None
    date_of_birth: Optional[str] = None


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str


class MessageVersionRead(BaseModel):
    text: str
    edited_at: str


class MessageHistoryRead(BaseModel):
    message_id: int
    current_text: str
    edited_at: Optional[str] = None
    versions: List[MessageVersionRead] = []
