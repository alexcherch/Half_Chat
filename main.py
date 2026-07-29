from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Field, Session, SQLModel, create_engine, select
from pydantic import BaseModel


# Описываем модель сообщения для базы данных
class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    text: str
    timestamp: str
    room: str = Field(default="general")


class MessageUpdate(BaseModel):
    text: str


# Настраиваем подключение к файлу SQLite
sqlite_file_name = "chat.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
connect_args = {"check_same_thread": False, "timeout": 30}  # Нужно для работы SQLite в поточном FastAPI
engine = create_engine(sqlite_url, connect_args=connect_args)

app = FastAPI(title="Lite Chat API with DB")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Создаем таблицу в базе данных при старте сервера
@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)


@app.post("/messages", response_model=Message, status_code=201)
def send_message(message_data: Message):
    """Отправка нового сообщения в конкретную комнату."""
    if not message_data.username.strip() or not message_data.text.strip():
        raise HTTPException(
            status_code=400, detail="Никнейм и текст не могут быть пустыми"
        )

    new_msg = Message(
        username=message_data.username.strip(),
        text=message_data.text.strip(),
        timestamp=datetime.now().strftime("%d.%m.%Y %H:%M"),
        # Если фронтенд не прислал комнату, запишем в "general"
        room=message_data.room.strip().lower() if message_data.room else "general"
    )

    with Session(engine) as session:
        session.add(new_msg)
        session.commit()
        session.refresh(new_msg)
        return new_msg


@app.get("/messages", response_model=List[Message])
def get_messages(
        after_id: int = Query(default=0),
        limit: int = Query(default=20, le=100),
        room: str = Query(default="general")  # <--- ДОБАВИЛИ ФИЛЬТР ПО КОМНАТЕ
):
    """Получение истории сообщений конкретной комнаты."""
    with Session(engine) as session:
        # Теперь выбираем сообщения, где ID > after_id И комната совпадает с запрошенной
        statement = (
            select(Message)
            .where(Message.id > after_id)
            .where(Message.room == room.lower())
            .order_by(Message.id.asc())
        )
        results = session.exec(statement).all()

        return results[-limit:] if results else []


@app.delete("/messages/{message_id}", status_code=200)
def delete_message(message_id: int):
    """
    Удаление сообщения по его уникальному ID.
    """
    with Session(engine) as session:
        # Ищем сообщение в базе по его ID
        statement = select(Message).where(Message.id == message_id)
        message = session.exec(statement).first()

        # Если такого сообщения нет, возвращаем ошибку 404
        if not message:
            raise HTTPException(
                status_code=404,
                detail=f"Сообщение с ID {message_id} не найдено"
            )

        # Удаляем сообщение и сохраняем изменения в файл
        session.delete(message)
        session.commit()

        # Возвращаем статус успеха
        return {"status": "success", "message": f"Сообщение {message_id} успешно удалено"}


@app.put("/messages/{message_id}", response_model=Message)
def update_message(message_id: int, update_data: MessageUpdate):
    """
    Редактирование текста сообщения по его ID.
    """
    # Проверяем, что новый текст не пустой
    if not update_data.text.strip():
        raise HTTPException(
            status_code=400, detail="Текст сообщения не может быть пустым"
        )

    with Session(engine) as session:
        # Ищем сообщение в базе
        statement = select(Message).where(Message.id == message_id)
        message = session.exec(statement).first()

        # Если сообщения с таким ID нет — возвращаем 404
        if not message:
            raise HTTPException(
                status_code=404,
                detail=f"Сообщение с ID {message_id} не найдено"
            )

        # Обновляем текст сообщения
        message.text = update_data.text.strip()

        # Опционально: добавляем пометку "(изм.)" к времени
        if " (изм.)" not in message.timestamp:
            message.timestamp += " (изм.)"

        # Сохраняем изменения в базу данных
        session.add(message)
        session.commit()
        session.refresh(message)

        return message


@app.get("/rooms", response_model=List[str])
def get_rooms():
    """
    Получение списка всех существующих комнат, в которых есть хотя бы одно сообщение.
    """
    with Session(engine) as session:
        # Выбираем уникальные (distinct) значения из колонки room
        statement = select(Message.room).distinct()
        results = session.exec(statement).all()

        # Возвращаем список строк (названий комнат)
        return results
