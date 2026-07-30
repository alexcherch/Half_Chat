from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    date_of_birth: Optional[str] = None


class Group(SQLModel, table=True):
    __tablename__ = "chat_group"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    created_by: str
    created_at: str


class GroupMember(SQLModel, table=True):
    __tablename__ = "group_member"
    id: Optional[int] = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="chat_group.id", index=True)
    username: str


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    text: str
    timestamp: str
    group_id: int = Field(default=1, foreign_key="chat_group.id", index=True)
