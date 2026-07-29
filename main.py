from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Field, Session, SQLModel, create_engine, select


# Описываем модель сообщения для базы данных
class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    text: str
    timestamp: str


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
    """Отправка нового сообщения и сохранение его в БД."""
    if not message_data.username.strip() or not message_data.text.strip():
        raise HTTPException(
            status_code=400, detail="Никнейм и текст не могут быть пустыми"
        )

    # Создаем объект сообщения с текущим временем
    new_msg = Message(
        username=message_data.username.strip(),
        text=message_data.text.strip(),
        timestamp=datetime.now().strftime("%d.%m.%Y %H:%M")
    )

    # Сохраняем в базу данных
    with Session(engine) as session:
        session.add(new_msg)
        session.commit()
        session.refresh(new_msg)  # Получаем сгенерированный базой id
        return new_msg


@app.get("/messages", response_model=List[Message])
def get_messages(after_id: int = Query(default=0), limit: int = Query(default=20, le=100)):
    """
    Получение истории сообщений.
    - after_id: вернуть сообщения с ID строго больше этого
    - limit: сколько максимум сообщений вернуть за один раз (по умолчанию 20, максимум 100)
    """
    with Session(engine) as session:
        # Формируем запрос с фильтром по ID и сортировкой по возрастанию
        statement = select(Message).where(Message.id > after_id).order_by(Message.id.asc())
        results = session.exec(statement).all()

        # Берем только последние 'limit' сообщений
        return results[-limit:] if results else []
