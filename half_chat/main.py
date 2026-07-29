from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from half_chat.database import init_db
from half_chat.routers import auth, messages

app = FastAPI(title="Lite Chat API with DB")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(messages.router)


@app.on_event("startup")
def on_startup():
    init_db()
