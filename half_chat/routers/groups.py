from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, func, select

from half_chat.auth import get_current_user
from half_chat.database import engine
from half_chat.models import Group, GroupBan, GroupMember, User
from half_chat.schemas import (
    AddMember,
    DirectCreate,
    DirectRead,
    GroupCreate,
    GroupRead,
    MemberRead,
    RoleUpdate,
)

router = APIRouter()


def find_direct_group(session: Session, user_a: str, user_b: str) -> Optional[Group]:
    ids_a = set(
        session.exec(select(GroupMember.group_id).where(GroupMember.username == user_a)).all()
    )
    ids_b = set(
        session.exec(select(GroupMember.group_id).where(GroupMember.username == user_b)).all()
    )
    for group_id in ids_a & ids_b:
        group = session.get(Group, group_id)
        if group and group.is_direct:
            return group
    return None


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
            created_at=datetime.now().isoformat(),
        )
        session.add(group)
        session.commit()
        session.refresh(group)

        session.add(GroupMember(group_id=group.id, username=current_user.username, role="admin"))
        session.commit()

        return GroupRead(
            id=group.id,  # type: ignore[arg-type]
            name=group.name,
            created_by=group.created_by,
            created_at=group.created_at,
            member_count=1,
        )


@router.post("/api/directs", response_model=DirectRead, status_code=201)
def create_direct(direct_data: DirectCreate, current_user: User = Depends(get_current_user)):
    peer = direct_data.username.strip()
    if not peer:
        raise HTTPException(status_code=400, detail="Имя пользователя не может быть пустым")
    if peer == current_user.username:
        raise HTTPException(status_code=400, detail="Нельзя создать личный чат с самим собой")

    with Session(engine) as session:
        peer_user = session.exec(select(User).where(User.username == peer)).first()
        if not peer_user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        existing = find_direct_group(session, current_user.username, peer)
        if existing:
            return DirectRead(id=existing.id, peer=peer, created_at=existing.created_at)  # type: ignore[arg-type]

        group = Group(
            name=peer,
            created_by=current_user.username,
            created_at=datetime.now().isoformat(),
            is_direct=True,
        )
        session.add(group)
        session.commit()
        session.refresh(group)

        session.add(GroupMember(group_id=group.id, username=current_user.username))
        session.add(GroupMember(group_id=group.id, username=peer))
        session.commit()

        return DirectRead(id=group.id, peer=peer, created_at=group.created_at)  # type: ignore[arg-type]


@router.get("/api/directs", response_model=List[DirectRead])
def list_directs(current_user: User = Depends(get_current_user)):
    with Session(engine) as session:
        user_group_ids = session.exec(
            select(GroupMember.group_id).where(GroupMember.username == current_user.username)
        ).all()

        groups = (
            session.exec(
                select(Group)
                .where(
                    Group.id.in_(user_group_ids),  # type: ignore[union-attr]
                    Group.is_direct == True,  # noqa: E712
                )
                .order_by(Group.id)  # type: ignore[arg-type]
            ).all()
            if user_group_ids
            else []
        )

        result = []
        for g in groups:
            members = session.exec(
                select(GroupMember.username).where(GroupMember.group_id == g.id)
            ).all()
            peer = next((m for m in members if m != current_user.username), "")
            result.append(DirectRead(id=g.id, peer=peer, created_at=g.created_at))  # type: ignore[arg-type]
        return result


@router.get("/api/groups", response_model=List[GroupRead])
def list_groups(current_user: User = Depends(get_current_user)):
    with Session(engine) as session:
        user_group_ids = session.exec(
            select(GroupMember.group_id).where(GroupMember.username == current_user.username)
        ).all()
        user_group_ids = [x for x in user_group_ids if x is not None]

        groups = (
            session.exec(
                select(Group)
                .where(
                    Group.id.in_(user_group_ids),  # type: ignore[union-attr,arg-type]
                    Group.is_direct == False,  # noqa: E712
                )
                .order_by(Group.id)  # type: ignore[arg-type]
            ).all()
            if user_group_ids
            else []
        )

        result = []
        for g in groups:
            count = session.exec(
                select(func.count(GroupMember.id)).where(GroupMember.group_id == g.id)  # type: ignore[arg-type]
            ).one()
            result.append(
                GroupRead(
                    id=g.id,  # type: ignore[arg-type]
                    name=g.name,
                    created_by=g.created_by,
                    created_at=g.created_at,
                    member_count=count,
                    pinned_message_id=g.pinned_message_id,
                )
            )
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
        if group.is_direct:
            raise HTTPException(status_code=400, detail="Нельзя добавлять участников в личный чат")

        user = session.exec(
            select(User).where(User.username == member_data.username.strip())
        ).first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        banned = session.exec(
            select(GroupBan).where(
                GroupBan.group_id == group_id,
                GroupBan.username == member_data.username.strip(),
            )
        ).first()
        if banned:
            raise HTTPException(status_code=403, detail="Пользователь забанен в этой группе")

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


@router.post("/api/groups/{group_id}/join", status_code=200)
def join_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
):
    with Session(engine) as session:
        group = session.get(Group, group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Группа не найдена")
        if group.is_direct:
            raise HTTPException(status_code=400, detail="Нельзя вступить в личный чат")

        banned = session.exec(
            select(GroupBan).where(
                GroupBan.group_id == group_id,
                GroupBan.username == current_user.username,
            )
        ).first()
        if banned:
            raise HTTPException(status_code=403, detail="Вы забанены в этой группе")

        existing = session.exec(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.username == current_user.username,
            )
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Вы уже в группе")

        session.add(GroupMember(group_id=group_id, username=current_user.username))
        session.commit()
        return {"status": "success", "group_id": group_id, "username": current_user.username}


@router.post("/api/groups/{group_id}/leave", status_code=200)
def leave_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
):
    with Session(engine) as session:
        group = session.get(Group, group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Группа не найдена")
        if group.is_direct:
            raise HTTPException(status_code=400, detail="Нельзя выйти из личного чата")

        existing = session.exec(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.username == current_user.username,
            )
        ).first()
        if not existing:
            raise HTTPException(status_code=400, detail="Вы не состоите в группе")

        session.delete(existing)
        session.commit()
        return {"status": "success", "group_id": group_id, "username": current_user.username}


@router.get("/api/groups/{group_id}/members", response_model=List[MemberRead])
def get_members(group_id: int):
    with Session(engine) as session:
        group = session.get(Group, group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Группа не найдена")

        members = session.exec(select(GroupMember).where(GroupMember.group_id == group_id)).all()
        return [
            MemberRead(
                username=m.username,
                role=m.role,
            )
            for m in members
        ]


@router.put("/api/groups/{group_id}/members/{username}/role", status_code=200)
def set_member_role(
    group_id: int,
    username: str,
    role_data: RoleUpdate,
    current_user: User = Depends(get_current_user),
):
    role = role_data.role.strip().lower()
    if role not in {"admin", "moderator", "member"}:
        raise HTTPException(
            status_code=400,
            detail="Роль должна быть admin, moderator или member",
        )

    with Session(engine) as session:
        group = session.get(Group, group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Группа не найдена")
        if group.is_direct:
            raise HTTPException(status_code=400, detail="В личных чатах нет ролей")

        actor = session.exec(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.username == current_user.username,
            )
        ).first()
        if not actor or actor.role != "admin":
            raise HTTPException(status_code=403, detail="Только админ может менять роли")

        if username == current_user.username:
            raise HTTPException(status_code=400, detail="Нельзя изменить собственную роль")

        membership = session.exec(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.username == username,
            )
        ).first()
        if not membership:
            raise HTTPException(status_code=404, detail="Участник не найден в группе")

        if membership.role == "admin" and role != "admin":
            admin_count = session.exec(
                select(func.count(GroupMember.id)).where(  # type: ignore[arg-type]
                    GroupMember.group_id == group_id,
                    GroupMember.role == "admin",
                )
            ).one()
            if admin_count <= 1:
                raise HTTPException(
                    status_code=400,
                    detail="Нельзя снять роль админа с последнего админа",
                )

        membership.role = role
        session.add(membership)
        session.commit()
        return {"status": "success", "group_id": group_id, "username": username, "role": role}


def get_admin_or_403(session: Session, group_id: int, username: str) -> GroupMember:
    actor = session.exec(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.username == username,
        )
    ).first()
    if not actor or actor.role != "admin":
        raise HTTPException(status_code=403, detail="Только админ может выполнить это действие")
    return actor


@router.delete("/api/groups/{group_id}/members/{username}", status_code=200)
def remove_member(
    group_id: int,
    username: str,
    current_user: User = Depends(get_current_user),
):
    with Session(engine) as session:
        group = session.get(Group, group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Группа не найдена")
        if group.is_direct:
            raise HTTPException(status_code=400, detail="Нельзя удалять участников личного чата")
        get_admin_or_403(session, group_id, current_user.username)

        if username == current_user.username:
            raise HTTPException(status_code=400, detail="Выйдите из группы через leave")

        membership = session.exec(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.username == username,
            )
        ).first()
        if not membership:
            raise HTTPException(status_code=404, detail="Участник не найден в группе")
        if membership.role == "admin":
            raise HTTPException(status_code=400, detail="Нельзя удалить админа")

        session.delete(membership)
        session.commit()
        return {"status": "success", "group_id": group_id, "username": username}


@router.post("/api/groups/{group_id}/members/{username}/ban", status_code=200)
def ban_member(
    group_id: int,
    username: str,
    current_user: User = Depends(get_current_user),
):
    with Session(engine) as session:
        group = session.get(Group, group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Группа не найдена")
        if group.is_direct:
            raise HTTPException(status_code=400, detail="Нельзя банить в личном чате")
        get_admin_or_403(session, group_id, current_user.username)

        if username == current_user.username:
            raise HTTPException(status_code=400, detail="Нельзя забанить самого себя")

        membership = session.exec(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.username == username,
            )
        ).first()
        if membership:
            if membership.role == "admin":
                raise HTTPException(status_code=400, detail="Нельзя забанить админа")
            session.delete(membership)

        existing_ban = session.exec(
            select(GroupBan).where(
                GroupBan.group_id == group_id,
                GroupBan.username == username,
            )
        ).first()
        if not existing_ban:
            session.add(GroupBan(group_id=group_id, username=username))
        session.commit()
        return {"status": "success", "group_id": group_id, "username": username, "banned": True}


@router.post("/api/groups/{group_id}/members/{username}/unban", status_code=200)
def unban_member(
    group_id: int,
    username: str,
    current_user: User = Depends(get_current_user),
):
    with Session(engine) as session:
        group = session.get(Group, group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Группа не найдена")
        get_admin_or_403(session, group_id, current_user.username)

        ban = session.exec(
            select(GroupBan).where(
                GroupBan.group_id == group_id,
                GroupBan.username == username,
            )
        ).first()
        if not ban:
            raise HTTPException(status_code=404, detail="Пользователь не в бане")

        session.delete(ban)
        session.commit()
        return {"status": "success", "group_id": group_id, "username": username, "banned": False}


@router.get("/api/groups/{group_id}/banned", response_model=List[str])
def get_banned_users(group_id: int, current_user: User = Depends(get_current_user)):
    with Session(engine) as session:
        group = session.get(Group, group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Группа не найдена")
        get_admin_or_403(session, group_id, current_user.username)

        banned = session.exec(select(GroupBan.username).where(GroupBan.group_id == group_id)).all()
        return banned
