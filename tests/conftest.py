import os
import urllib.parse

try:
    from nedochat.db_config import DATABASE_URL as _DEV_URL  # noqa: E402
except ImportError:
    _DEV_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/nedochat")

_TEST_DB = "nedochat_test"
_parts = urllib.parse.urlparse(_DEV_URL)
os.environ["DATABASE_URL"] = _parts._replace(path="/" + _TEST_DB).geturl()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

from nedochat.database import engine  # noqa: E402
from nedochat.main import app  # noqa: E402
from nedochat.rate_limit import limiter  # noqa: E402

PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63f8ffff3f03000606013f2566b91d0000000049454e44ae426082"
)


@pytest.fixture(scope="session", autouse=True)
def _disable_rate_limit():
    limiter.enabled = False
    yield


@pytest.fixture(autouse=True)
def _clean_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def register(client, username, password="pass123", **extra):
    return client.post("/api/register", json={"username": username, "password": password, **extra})


def login(client, username, password="pass123"):
    return client.post("/api/login", json={"username": username, "password": password})


def token_of(client, username, password="pass123"):
    return login(client, username, password).json()["access_token"]


def auth_headers(client, username, password="pass123"):
    return {"Authorization": f"Bearer {token_of(client, username, password)}"}


def create_group(client, username, name, members=None):
    r = client.post(
        "/api/groups",
        json={"name": name},
        headers=auth_headers(client, username),
    )
    assert r.status_code == 201, r.text
    gid = r.json()["id"]
    for m in members or []:
        resp = client.post(
            f"/api/groups/{gid}/members",
            json={"username": m},
            headers=auth_headers(client, username),
        )
        assert resp.status_code == 200, resp.text
    return gid


def send_message(client, username, group_id, text):
    return client.post(
        "/api/messages",
        json={"group_id": group_id, "text": text},
        headers=auth_headers(client, username),
    )
