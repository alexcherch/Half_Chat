import io

from tests.conftest import PNG_1PX, auth_headers, create_group, register


def test_create_group(client):
    register(client, "alice")
    gid = create_group(client, "alice", "team")
    r = client.get("/api/groups", headers=auth_headers(client, "alice"))
    names = [g["name"] for g in r.json()]
    assert "team" in names
    details = client.get(f"/api/groups/{gid}", headers=auth_headers(client, "alice")).json()
    assert details["name"] == "team"


def test_group_details_require_membership(client):
    register(client, "alice")
    register(client, "bob")
    gid = create_group(client, "alice", "private")
    assert client.get(f"/api/groups/{gid}", headers=auth_headers(client, "bob")).status_code == 403


def test_update_group_admin_only(client):
    register(client, "alice")
    register(client, "bob")
    gid = create_group(client, "alice", "team", members=["bob"])
    ok = client.put(
        f"/api/groups/{gid}", json={"description": "desc"}, headers=auth_headers(client, "alice")
    )
    assert ok.status_code == 200
    assert ok.json()["description"] == "desc"
    assert (
        client.put(
            f"/api/groups/{gid}", json={"name": "hacked"}, headers=auth_headers(client, "bob")
        ).status_code
        == 403
    )


def test_add_member_and_roles(client):
    register(client, "alice")
    register(client, "bob")
    register(client, "carol")
    gid = create_group(client, "alice", "team")
    r = client.post(
        f"/api/groups/{gid}/members",
        json={"username": "bob"},
        headers=auth_headers(client, "alice"),
    )
    assert r.status_code == 200
    r = client.put(
        f"/api/groups/{gid}/members/bob/role",
        json={"role": "admin"},
        headers=auth_headers(client, "alice"),
    )
    assert r.status_code == 200
    members = client.get(f"/api/groups/{gid}/members", headers=auth_headers(client, "alice")).json()
    roles = {m["username"]: m["role"] for m in members}
    assert roles["bob"] == "admin"
    assert (
        client.put(
            f"/api/groups/{gid}/members/carol/role",
            json={"role": "admin"},
            headers=auth_headers(client, "bob"),
        ).status_code
        == 404
    )


def test_join_leave(client):
    register(client, "alice")
    register(client, "bob")
    gid = create_group(client, "alice", "open")
    assert (
        client.post(f"/api/groups/{gid}/join", headers=auth_headers(client, "bob")).status_code
        == 200
    )
    assert (
        client.post(f"/api/groups/{gid}/leave", headers=auth_headers(client, "bob")).status_code
        == 200
    )


def test_ban_flow(client):
    register(client, "alice")
    register(client, "bob")
    gid = create_group(client, "alice", "team", members=["bob"])
    h = auth_headers(client, "alice")
    assert client.post(f"/api/groups/{gid}/members/bob/ban", headers=h).status_code == 200
    banned = client.get(f"/api/groups/{gid}/banned", headers=h).json()
    assert "bob" in banned
    assert client.post(f"/api/groups/{gid}/members/bob/unban", headers=h).status_code == 200
    banned = client.get(f"/api/groups/{gid}/banned", headers=h).json()
    assert "bob" not in banned


def test_mute_flow(client):
    register(client, "alice")
    register(client, "bob")
    gid = create_group(client, "alice", "team", members=["bob"])
    h = auth_headers(client, "alice")
    assert client.post(f"/api/groups/{gid}/members/bob/mute", headers=h).status_code == 200
    r = client.post(
        "/api/messages",
        json={"group_id": gid, "text": "muted"},
        headers=auth_headers(client, "bob"),
    )
    assert r.status_code == 403
    assert client.post(f"/api/groups/{gid}/members/bob/unmute", headers=h).status_code == 200
    assert (
        client.post(
            "/api/messages",
            json={"group_id": gid, "text": "ok"},
            headers=auth_headers(client, "bob"),
        ).status_code
        == 201
    )


def test_direct_chat(client):
    register(client, "alice")
    register(client, "bob")
    h = auth_headers(client, "alice")
    r1 = client.post("/api/directs", json={"username": "bob"}, headers=h)
    r2 = client.post("/api/directs", json={"username": "bob"}, headers=h)
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]
    directs = client.get("/api/directs", headers=h).json()
    peers = {d["peer"] for d in directs}
    assert "bob" in peers


def test_group_avatar(client):
    register(client, "alice")
    gid = create_group(client, "alice", "team")
    r = client.post(
        f"/api/groups/{gid}/avatar",
        files={"file": ("g.png", io.BytesIO(PNG_1PX), "image/png")},
        headers=auth_headers(client, "alice"),
    )
    assert r.status_code == 200
    assert "/static/avatars/" in r.json()["avatar_url"]
