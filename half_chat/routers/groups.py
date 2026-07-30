from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func

from half_chat.auth import get_current_user
from half_chat.database import engine
from half_chat.models import Group, GroupMember, User
from half_chat.schemas import AddMember, GroupCreate, GroupRead

router = APIRouter()


@router.post("/api/groups", response_model=GroupRead, status_code=201)
def create_group(
    group_data: GroupCreate,
    current_user: User = Depends(get_current_user),
):
    if not group_data.name.strip():
        raise HTTPException(status_code=400, detail="Название группы не может быть пустым")

    with Session(engine) as session:
        group = Group(
            name=group_data.name.strip(),
            created_by=current_user.username,
            created_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
        )
        session.add(group)
        session.commit()
        session.refresh(group)

        session.add(GroupMember(group_id=group.id, username=current_user.username))
        session.commit()

        return GroupRead(
            id=group.id,
            name=group.name,
            created_by=group.created_by,
            created_at=group.created_at,
            member_count=1,
        )


@router.get("/api/groups", response_model=List[GroupRead])
def list_groups():
    with Session(engine) as session:
        groups = session.exec(
            select(Group).order_by(Group.id)
        ).all()

        result = []
        for g in groups:
            count = session.exec(
                select(func.count(GroupMember.id)).where(GroupMember.group_id == g.id)
            ).one()
            result.append(GroupRead(
                id=g.id,
                name=g.name,
                created_by=g.created_by,
                created_at=g.created_at,
                member_count=count,
            ))
        return result


@router.post("/api/groups/{group_id}/members", status_code=200)
def add_member(
    group_id: int,
    member_data: AddMember,
    current_user: User = Depends(get_current_user),
):
    if not member_data.username.strip():
        raise HTTPException(status_code=400, detail="Имя пользователя не может быть пустым")

    with Session(engine) as session:
        group = session.get(Group, group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Группа не найдена")

        user = session.exec(
            select(User).where(User.username == member_data.username.strip())
        ).first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        existing = session.exec(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.username == member_data.username.strip(),
            )
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Пользователь уже в группе")

        session.add(GroupMember(group_id=group_id, username=member_data.username.strip()))
        session.commit()
        return {"status": "success", "username": member_data.username.strip(), "group_id": group_id}


@router.get("/api/groups/{group_id}/members", response_model=List[str])
def get_members(group_id: int):
    with Session(engine) as session:
        group = session.get(Group, group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Группа не найдена")

        members = session.exec(
            select(GroupMember.username).where(GroupMember.group_id == group_id)
        ).all()
        return members
