import os
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select

from nedochat.database import engine, init_db
from nedochat.models import Group
from nedochat.routers import auth, groups, messages, users

app = FastAPI(title="Nedochat")

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
app.include_router(users.router)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(os.path.join(STATIC_DIR, "avatars"), exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def on_startup():
    init_db()
    with Session(engine) as session:
        existing = session.exec(select(Group).where(Group.name == "general")).first()
        if not existing:
            session.add(
                Group(
                    name="general",
                    created_by="system",
                    created_at=datetime.now().isoformat(),
                )
            )
            session.commit()
