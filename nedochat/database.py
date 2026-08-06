from sqlmodel import Session, SQLModel, create_engine

from nedochat.config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
