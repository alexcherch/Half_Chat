from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    display_name: Optional[str] = None
    password_hash: str
    date_of_birth: Optional[str] = None
    avatar_url: Optional[str] = None


class Group(SQLModel, table=True):
    __tablename__ = "chat_group"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    created_by: str
    created_at: str
    is_direct: bool = Field(default=False)
    pinned_message_id: Optional[int] = Field(default=None)


class GroupMember(SQLModel, table=True):
    __tablename__ = "group_member"
    id: Optional[int] = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="chat_group.id", index=True)
    username: str
    role: str = Field(default="member")
    muted: bool = Field(default=False)


class GroupBan(SQLModel, table=True):
    __tablename__ = "group_ban"
    id: Optional[int] = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="chat_group.id", index=True)
    username: str


class UserBlock(SQLModel, table=True):
    __tablename__ = "user_block"
    __table_args__ = (UniqueConstraint("blocker_id", "blocked_id", name="uq_user_block_pair"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    blocker_id: int = Field(foreign_key="user.id", index=True)
    blocked_id: int = Field(foreign_key="user.id", index=True)


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    text: str
    timestamp: str
    group_id: int = Field(default=1, foreign_key="chat_group.id", index=True)
    reply_to_id: Optional[int] = Field(default=None, foreign_key="message.id")
    forwarded_from_id: Optional[int] = Field(default=None, foreign_key="message.id")
    forwarded_group_id: Optional[int] = Field(default=None)
    deleted: bool = Field(default=False)
    edited_at: Optional[str] = None


class MessageVersion(SQLModel, table=True):
    __tablename__ = "message_version"
    id: Optional[int] = Field(default=None, primary_key=True)
    message_id: int = Field(foreign_key="message.id", index=True)
    text: str
    edited_at: str
