from tests.conftest import auth_headers, login, register, token_of


def test_register_success(client):
    r = register(client, "alice")
    assert r.status_code == 201
    assert r.json() == {"status": "success", "username": "alice"}


def test_register_duplicate(client):
    register(client, "alice")
    r = register(client, "alice")
    assert r.status_code == 400
    assert "уже существует" in r.json()["detail"]


def test_register_empty_fields(client):
    assert register(client, "   ").status_code == 400
    assert register(client, "bob", password="  ").status_code == 400


def test_login_success(client):
    register(client, "alice")
    r = login(client, "alice")
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_login_wrong_password(client):
    register(client, "alice")
    assert login(client, "alice", "nope").status_code == 401


def test_login_unknown_user(client):
    assert login(client, "ghost").status_code == 401


def test_register_adds_to_general(client):
    register(client, "alice")
    token = token_of(client, "alice")
    r = client.get("/api/groups", headers={"Authorization": f"Bearer {token}"})
    names = [g["name"] for g in r.json()]
    assert "general" in names


def test_me_requires_auth(client):
    assert client.get("/api/users/me").status_code == 401


def test_profile_fields(client):
    register(client, "alice", display_name="Al", date_of_birth="2000-01-01")
    r = client.get("/api/users/me", headers=auth_headers(client, "alice"))
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "alice"
    assert body["display_name"] == "Al"
    assert body["date_of_birth"] == "2000-01-01"
