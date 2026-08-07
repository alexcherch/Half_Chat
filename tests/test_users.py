import io

from tests.conftest import PNG_1PX, auth_headers, register, token_of


def test_search_fuzzy(client):
    register(client, "alice")
    register(client, "bob")
    r = client.get("/api/users", params={"q": "ali"})
    assert r.status_code == 200
    usernames = [u["username"] for u in r.json()]
    assert "alice" in usernames
    assert "bob" not in usernames


def test_get_user_exact(client):
    register(client, "alice", display_name="Al")
    r = client.get("/api/users/alice")
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "alice"
    assert body["display_name"] == "Al"


def test_get_user_exact_case_sensitive(client):
    register(client, "alice")
    assert client.get("/api/users/Alice").status_code == 404
    assert client.get("/api/users/nobody").status_code == 404


def test_update_profile(client):
    register(client, "alice")
    r = client.put(
        "/api/users/me",
        json={"display_name": "Al", "date_of_birth": "2000-05-05"},
        headers=auth_headers(client, "alice"),
    )
    assert r.status_code == 200
    assert (
        client.get("/api/users/me", headers=auth_headers(client, "alice")).json()["display_name"]
        == "Al"
    )


def test_change_password(client):
    register(client, "alice")
    headers = auth_headers(client, "alice")
    r = client.put(
        "/api/users/me/password",
        json={"current_password": "pass123", "new_password": "new456"},
        headers=headers,
    )
    assert r.status_code == 200
    assert (
        client.post("/api/login", json={"username": "alice", "password": "new456"}).status_code
        == 200
    )
    assert login_wrong(client, "alice")


def login_wrong(client, username):
    return (
        client.post("/api/login", json={"username": username, "password": "pass123"}).status_code
        == 401
    )


def test_change_password_wrong_current(client):
    register(client, "alice")
    r = client.put(
        "/api/users/me/password",
        json={"current_password": "bad", "new_password": "new456"},
        headers=auth_headers(client, "alice"),
    )
    assert r.status_code == 400


def test_upload_avatar(client):
    register(client, "alice")
    r = client.put(
        "/api/users/me/avatar",
        files={"file": ("a.png", io.BytesIO(PNG_1PX), "image/png")},
        headers=auth_headers(client, "alice"),
    )
    assert r.status_code == 200
    assert "/static/avatars/" in r.json()["avatar_url"]


def test_upload_avatar_invalid(client):
    register(client, "alice")
    r = client.put(
        "/api/users/me/avatar",
        files={"file": ("a.png", io.BytesIO(b"not an image"), "image/png")},
        headers=auth_headers(client, "alice"),
    )
    assert r.status_code == 400


def test_block_flow(client):
    register(client, "alice")
    register(client, "bob")
    h = auth_headers(client, "alice")
    assert client.post("/api/users/bob/block", headers=h).status_code == 200
    assert client.get("/api/users/me/blocked", headers=h).json() == ["bob"]
    assert client.post("/api/users/bob/block", headers=h).status_code == 400
    assert client.post("/api/users/alice/block", headers=h).status_code == 400
    assert client.post("/api/users/ghost/block", headers=h).status_code == 404
    assert client.post("/api/users/bob/unblock", headers=h).status_code == 200
    assert client.get("/api/users/me/blocked", headers=h).json() == []
    assert client.post("/api/users/bob/unblock", headers=h).status_code == 404


def test_block_blocks_direct(client):
    register(client, "alice")
    register(client, "bob")
    token_alice = token_of(client, "alice")
    dm = client.post(
        "/api/directs",
        json={"username": "bob"},
        headers={"Authorization": f"Bearer {token_alice}"},
    ).json()
    client.post(
        "/api/users/bob/block",
        headers={"Authorization": f"Bearer {token_alice}"},
    )
    r = client.post(
        "/api/messages",
        json={"group_id": dm["id"], "text": "hello"},
        headers=auth_headers(client, "bob"),
    )
    assert r.status_code == 403
