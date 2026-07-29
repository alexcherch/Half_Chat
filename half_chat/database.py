from sqlmodel import Session, SQLModel, create_engine

from half_chat.config import CONNECT_ARGS, SQLITE_URL

engine = create_engine(SQLITE_URL, connect_args=CONNECT_ARGS)


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
