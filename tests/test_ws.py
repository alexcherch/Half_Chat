# mypy: disable-error-code=arg-type
import asyncio

from fastapi.testclient import TestClient

from nedochat.main import app
from nedochat.ws import ConnectionManager


class FakeWS:
    def __init__(self):
        self.sent = []

    async def accept(self):
        pass

    async def send_json(self, payload):
        self.sent.append(payload)


def _run(coro):
    return asyncio.run(coro)


def test_broadcast_delivers_to_group_members_only():
    a = FakeWS()
    b = FakeWS()
    c = FakeWS()
    mgr = ConnectionManager()

    async def run():
        await mgr.connect(1, a)
        await mgr.connect(1, b)
        await mgr.connect(2, c)
        await mgr.broadcast(1, {"type": "new_message", "n": 1})
        await mgr.broadcast(99, {"type": "ghost", "n": 2})

    _run(run())
    assert a.sent == [{"type": "new_message", "n": 1}]
    assert b.sent == [{"type": "new_message", "n": 1}]
    assert c.sent == []


def test_disconnect_cleans_and_pops_empty_group():
    a = FakeWS()
    b = FakeWS()
    mgr = ConnectionManager()

    async def run():
        await mgr.connect(5, a)
        await mgr.connect(5, b)
        mgr.disconnect(5, a)
        assert 5 in mgr.active_connections
        mgr.disconnect(5, b)
        assert 5 not in mgr.active_connections

    _run(run())


def test_disconnect_ignores_unknown_ws():
    mgr = ConnectionManager()
    mgr.disconnect(5, FakeWS())  # not registered -> no crash
    mgr.disconnect(5, FakeWS())


def test_user_presence_tracking():
    a = FakeWS()
    b = FakeWS()
    mgr = ConnectionManager()

    async def run():
        await mgr.connect_user("alice", a)
        assert mgr.is_online("alice") is True
        await mgr.send_to_user("alice", {"type": "mention", "n": 1})
        mgr.disconnect_user("alice", a)
        assert mgr.is_online("alice") is False
        await mgr.connect_user("bob", b)

    _run(run())
    assert a.sent == [{"type": "mention", "n": 1}]


def test_send_to_user_removes_dead_socket():
    class BrokenWS(FakeWS):
        async def send_json(self, payload):
            raise RuntimeError("gone")

    a = BrokenWS()
    mgr = ConnectionManager()

    async def run():
        await mgr.connect_user("carol", a)
        await mgr.send_to_user("carol", {"type": "mention"})
        assert mgr.is_online("carol") is False

    _run(run())


def test_broadcast_removes_dead_socket():
    class BrokenWS(FakeWS):
        async def send_json(self, payload):
            raise RuntimeError("gone")

    a = BrokenWS()
    mgr = ConnectionManager()

    async def run():
        await mgr.connect(1, a)
        await mgr.broadcast(1, {"type": "new_message"})
        assert a not in mgr.active_connections.get(1, [])

    _run(run())


def test_ws_plain_get_returns_426():
    client = TestClient(app)
    r = client.get("/api/ws/1")
    assert r.status_code == 426
    assert "WebSocket" in r.json()["detail"]
