import re
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlmodel import Session, select

from half_chat.auth import get_current_user, get_optional_user
from half_chat.config import ALGORITHM, SECRET_KEY
from half_chat.database import engine
from half_chat.models import Group, GroupMember, Message, User
from half_chat.schemas import ForwardCreate, MessageUpdate
from half_chat.ws import manager

router = APIRouter()

MENTION_RE = re.compile(r"@(\w+)")


def is_group_admin(session: Session, group_id: int, username: str) -> bool:
    membership = session.exec(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.username == username,
        )
    ).first()
    return bool(membership and membership.role == "admin")


def get_ws_username(websocket: WebSocket) -> str | None:
    token = websocket.query_params.get("token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        return username if isinstance(username, str) else None
    except JWTError:
        return None


def _check_can_post(session: Session, group_id: int, username: str) -> None:
    membership = session.exec(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.username == username,
        )
    ).first()
    if membership and membership.muted:
        raise HTTPException(
            status_code=403,
            detail="Вы не можете писать сообщения в этой группе",
        )


@router.websocket("/api/ws/{group_id}")
async def websocket_endpoint(websocket: WebSocket, group_id: int):
    await manager.connect(group_id, websocket)
    username = get_ws_username(websocket)
    if username:
        await manager.connect_user(username, websocket)
        await manager.broadcast(
            group_id, {"type": "presence", "username": username, "online": True}
        )
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(group_id, websocket)
        if username:
            manager.disconnect_user(username, websocket)
            if not manager.is_online(username):
                await manager.broadcast(
                    group_id,
                    {"type": "presence", "username": username, "online": False},
                )


@router.post("/api/messages", response_model=Message, status_code=201)
async def send_message(
    message_data: Message,
    current_user: User = Depends(get_current_user),
):
    if not message_data.text.strip():
        raise HTTPException(status_code=400, detail="Текст сообщения не может быть пустым")

    with Session(engine) as session:
        group = session.get(Group, message_data.group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Группа не найдена")

        _check_can_post(session, group.id, current_user.username)  # type: ignore[arg-type]

        if message_data.reply_to_id:
            reply_msg = session.get(Message, message_data.reply_to_id)
            if not reply_msg:
                raise HTTPException(
                    status_code=404,
                    detail=f"Сообщение {message_data.reply_to_id} не найдено",
                )

        new_msg = Message(
            username=current_user.username,
            text=message_data.text.strip(),
            timestamp=datetime.now().isoformat(),
            group_id=group.id,
            reply_to_id=message_data.reply_to_id,
        )
        session.add(new_msg)
        session.commit()
        session.refresh(new_msg)

        mentioned = set(MENTION_RE.findall(new_msg.text))
        known_mentions: List[str] = []
        if mentioned:
            known_mentions = list(
                session.exec(
                    select(User.username).where(User.username.in_(mentioned))  # type: ignore[attr-defined]
                ).all()
            )

    payload = new_msg.model_dump()
    await manager.broadcast(new_msg.group_id, {"type": "new_message", "message": payload})

    for mention in known_mentions:
        await manager.send_to_user(
            mention,
            {
                "type": "mention",
                "message": payload,
                "from": current_user.username,
            },
        )
    return new_msg


@router.get("/api/messages", response_model=List[Message])
def get_messages(
    group_id: int = Query(default=1),
    after_id: int = Query(default=0),
    limit: int = Query(default=20, le=100),
    current_user: Optional[User] = Depends(get_optional_user),
):
    with Session(engine) as session:
        group = session.get(Group, group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Группа не найдена")

        current_username = current_user.username if current_user else None
        is_admin = False
        if current_user:
            is_admin = is_group_admin(session, group_id, current_user.username)

        statement = (
            select(Message)
            .where(Message.group_id == group_id)
            .where(Message.id > after_id)  # type: ignore[operator]
            .order_by(Message.id.asc())  # type: ignore[union-attr]
        )
        results = session.exec(statement).all()

        visible: List[Message] = []
        for msg in results:
            if not msg.deleted:
                visible.append(msg)
            elif group.is_direct:
                if current_username and msg.username == current_username:
                    visible.append(msg)
            elif is_admin:
                visible.append(msg)
        return visible[-limit:] if visible else []


@router.post("/api/messages/{message_id}/forward", response_model=Message, status_code=201)
async def forward_message(
    message_id: int,
    forward_data: ForwardCreate,
    current_user: User = Depends(get_current_user),
):
    with Session(engine) as session:
        original = session.exec(select(Message).where(Message.id == message_id)).first()
        if not original:
            raise HTTPException(status_code=404, detail=f"Сообщение с ID {message_id} не найдено")

        target_group = session.get(Group, forward_data.group_id)
        if not target_group:
            raise HTTPException(status_code=404, detail="Группа не найдена")

        _check_can_post(session, target_group.id, current_user.username)  # type: ignore[arg-type]

        new_msg = Message(
            username=current_user.username,
            text=original.text,
            timestamp=datetime.now().isoformat(),
            group_id=target_group.id,
            forwarded_from_id=original.id,
            forwarded_group_id=original.group_id,
        )
        session.add(new_msg)
        session.commit()
        session.refresh(new_msg)

    payload = new_msg.model_dump()
    await manager.broadcast(new_msg.group_id, {"type": "new_message", "message": payload})
    return new_msg


@router.post("/api/messages/{message_id}/pin", status_code=200)
async def pin_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
):
    with Session(engine) as session:
        message = session.exec(select(Message).where(Message.id == message_id)).first()
        if not message:
            raise HTTPException(status_code=404, detail=f"Сообщение с ID {message_id} не найдено")

        group = session.get(Group, message.group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Группа не найдена")

        group.pinned_message_id = message.id
        group_id = message.group_id
        message_dict = message.model_dump()
        session.add(group)
        session.commit()

    await manager.broadcast(
        group_id,
        {"type": "pin_message", "message_id": message_id, "message": message_dict},
    )
    return {"status": "success", "group_id": group_id, "message_id": message_id}


@router.post("/api/messages/{message_id}/unpin", status_code=200)
async def unpin_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
):
    with Session(engine) as session:
        message = session.exec(select(Message).where(Message.id == message_id)).first()
        if not message:
            raise HTTPException(status_code=404, detail=f"Сообщение с ID {message_id} не найдено")

        group = session.get(Group, message.group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Группа не найдена")

        if group.pinned_message_id != message.id:
            raise HTTPException(status_code=400, detail="Сообщение не закреплено в этой группе")

        group.pinned_message_id = None
        group_id = message.group_id
        session.add(group)
        session.commit()

    await manager.broadcast(
        group_id,
        {"type": "unpin_message", "message_id": message_id},
    )
    return {"status": "success", "group_id": group_id, "message_id": message_id}


@router.delete("/api/messages/{message_id}", status_code=200)
async def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
):
    with Session(engine) as session:
        message = session.exec(select(Message).where(Message.id == message_id)).first()

        if not message:
            raise HTTPException(
                status_code=404,
                detail=f"Сообщение с ID {message_id} не найдено",
            )

        if message.username != current_user.username:
            raise HTTPException(
                status_code=403,
                detail="Нельзя удалить чужое сообщение",
            )

        group_id = message.group_id
        group = session.get(Group, group_id)
        if group and group.pinned_message_id == message.id:
            group.pinned_message_id = None
            session.add(group)

        message.deleted = True
        message_dict = message.model_dump()
        session.add(message)
        session.commit()

    await manager.broadcast(
        group_id,
        {"type": "delete_message", "message_id": message_id, "message": message_dict},
    )
    return {
        "status": "success",
        "message": f"Сообщение {message_id} успешно удалено",
    }


@router.put("/api/messages/{message_id}", response_model=Message)
async def update_message(
    message_id: int,
    update_data: MessageUpdate,
    current_user: User = Depends(get_current_user),
):
    if not update_data.text.strip():
        raise HTTPException(status_code=400, detail="Текст сообщения не может быть пустым")

    with Session(engine) as session:
        message = session.exec(select(Message).where(Message.id == message_id)).first()

        if not message:
            raise HTTPException(
                status_code=404,
                detail=f"Сообщение с ID {message_id} не найдено",
            )

        if message.username != current_user.username:
            raise HTTPException(
                status_code=403,
                detail="Нельзя редактировать чужое сообщение",
            )

        message.text = update_data.text.strip()

        session.add(message)
        session.commit()
        session.refresh(message)

    await manager.broadcast(
        message.group_id,
        {"type": "update_message", "message": message.model_dump()},
    )
    return message
