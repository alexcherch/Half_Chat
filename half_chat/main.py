from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from half_chat.database import engine, init_db
from half_chat.models import Group
from half_chat.routers import auth, groups, messages

app = FastAPI(title="Half Chat")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(groups.router)
app.include_router(messages.router)


@app.on_event("startup")
def on_startup():
    init_db()
    with Session(engine) as session:
        existing = session.exec(select(Group).where(Group.name == "general")).first()
        if not existing:
            session.add(Group(
                name="general",
                created_by="system",
                created_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
            ))
            session.commit()
