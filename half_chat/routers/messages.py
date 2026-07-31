from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from half_chat.auth import get_current_user
from half_chat.database import engine
from half_chat.models import Group, Message, User
from half_chat.schemas import MessageUpdate
from half_chat.ws import manager

router = APIRouter()


@router.websocket("/api/ws/{group_id}")
async def websocket_endpoint(websocket: WebSocket, group_id: int):
    await manager.connect(group_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(group_id, websocket)


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

    await manager.broadcast(
        new_msg.group_id,
        {"type": "new_message", "message": new_msg.model_dump()},
    )
    return new_msg


@router.get("/api/messages", response_model=List[Message])
def get_messages(
    group_id: int = Query(default=1),
    after_id: int = Query(default=0),
    limit: int = Query(default=20, le=100),
):
    with Session(engine) as session:
        group = session.get(Group, group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Группа не найдена")

        statement = (
            select(Message)
            .where(Message.group_id == group_id)
            .where(Message.id > after_id)  # type: ignore[operator]
            .order_by(Message.id.asc())  # type: ignore[union-attr]
        )
        results = session.exec(statement).all()
        return results[-limit:] if results else []


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
        session.delete(message)
        session.commit()

    await manager.broadcast(group_id, {"type": "delete_message", "message_id": message_id})
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
