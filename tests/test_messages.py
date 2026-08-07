from tests.conftest import auth_headers, create_group, register, send_message


def _gid_for(client, username, members=()):
    return create_group(client, username, "chat", members=list(members))


def _send_group(client, username, text, gid):
    r = send_message(client, username, gid, text)
    assert r.status_code == 201, r.text
    return r.json()


def test_send_and_list(client):
    register(client, "alice")
    gid = _gid_for(client, "alice")
    _send_group(client, "alice", "hello", gid)
    r = client.get("/api/messages", params={"group_id": gid}, headers=auth_headers(client, "alice"))
    assert r.status_code == 200
    assert any(m["text"] == "hello" for m in r.json())


def test_pagination_after_id(client):
    register(client, "alice")
    gid = _gid_for(client, "alice")
    sent = [_send_group(client, "alice", f"m{i}", gid)["id"] for i in range(5)]
    r = client.get(
        "/api/messages",
        params={"group_id": gid, "after_id": sent[1], "limit": 100},
        headers=auth_headers(client, "alice"),
    )
    ids = [m["id"] for m in r.json()]
    assert sent[2] in ids and sent[4] in ids
    assert sent[0] not in ids


def test_reply(client):
    register(client, "alice")
    gid = _gid_for(client, "alice")
    m = _send_group(client, "alice", "original", gid)
    r = client.post(
        "/api/messages",
        json={"group_id": gid, "text": "reply", "reply_to_id": m["id"]},
        headers=auth_headers(client, "alice"),
    )
    assert r.status_code == 201
    assert r.json()["reply_to_id"] == m["id"]


def test_edit_and_history(client):
    register(client, "alice")
    gid = _gid_for(client, "alice")
    m = _send_group(client, "alice", "v1", gid)
    assert (
        client.get(
            f"/api/messages/{m['id']}/history", headers=auth_headers(client, "alice")
        ).json()["edited_at"]
        is None
    )

    r = client.put(
        f"/api/messages/{m['id']}", json={"text": "v2"}, headers=auth_headers(client, "alice")
    )
    assert r.status_code == 200
    assert r.json()["edited_at"] is not None

    client.put(
        f"/api/messages/{m['id']}", json={"text": "v2"}, headers=auth_headers(client, "alice")
    )
    hist = client.get(
        f"/api/messages/{m['id']}/history", headers=auth_headers(client, "alice")
    ).json()
    assert len(hist["versions"]) == 1

    client.put(
        f"/api/messages/{m['id']}", json={"text": "v3"}, headers=auth_headers(client, "alice")
    )
    hist = client.get(
        f"/api/messages/{m['id']}/history", headers=auth_headers(client, "alice")
    ).json()
    assert [v["text"] for v in hist["versions"]] == ["v1", "v2"]
    assert hist["current_text"] == "v3"


def test_edit_forbidden_for_others(client):
    register(client, "alice")
    register(client, "bob")
    gid = create_group(client, "alice", "chat", members=["bob"])
    m = _send_group(client, "alice", "v1", gid)
    r = client.put(
        f"/api/messages/{m['id']}", json={"text": "hack"}, headers=auth_headers(client, "bob")
    )
    assert r.status_code == 403


def test_delete_soft(client):
    register(client, "alice")
    register(client, "bob")
    gid = create_group(client, "alice", "chat", members=["bob"])
    m = _send_group(client, "alice", "bye", gid)
    assert (
        client.delete(f"/api/messages/{m['id']}", headers=auth_headers(client, "alice")).status_code
        == 200
    )
    r = client.get("/api/messages", params={"group_id": gid}, headers=auth_headers(client, "bob"))
    assert not any(x["id"] == m["id"] for x in r.json())


def test_forward(client):
    register(client, "alice")
    gid = _gid_for(client, "alice")
    m = _send_group(client, "alice", "src", gid)
    r = client.post(
        f"/api/messages/{m['id']}/forward",
        json={"group_id": gid},
        headers=auth_headers(client, "alice"),
    )
    assert r.status_code == 201
    assert r.json()["forwarded_from_id"] == m["id"]


def test_pin_unpin(client):
    register(client, "alice")
    gid = _gid_for(client, "alice")
    m = _send_group(client, "alice", "pinme", gid)
    assert (
        client.post(
            f"/api/messages/{m['id']}/pin", headers=auth_headers(client, "alice")
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/messages/{m['id']}/unpin", headers=auth_headers(client, "alice")
        ).status_code
        == 200
    )


def test_search_messages(client):
    register(client, "alice")
    gid = _gid_for(client, "alice")
    _send_group(client, "alice", "unique needle text", gid)
    _send_group(client, "alice", "other", gid)
    r = client.get(
        "/api/messages/search", params={"q": "needle"}, headers=auth_headers(client, "alice")
    )
    assert any(m["text"] == "unique needle text" for m in r.json())


def test_mention(client):
    register(client, "alice")
    gid = _gid_for(client, "alice")
    r = client.post(
        "/api/messages",
        json={"group_id": gid, "text": "hey @alice"},
        headers=auth_headers(client, "alice"),
    )
    assert r.status_code == 201


def test_blocked_messages_hidden(client):
    register(client, "alice")
    register(client, "bob")
    gid = create_group(client, "alice", "pub", members=["bob"])
    _send_group(client, "alice", "alice msg", gid)
    _send_group(client, "bob", "bob msg", gid)
    client.post("/api/users/bob/block", headers=auth_headers(client, "alice"))
    r = client.get("/api/messages", params={"group_id": gid}, headers=auth_headers(client, "alice"))
    texts = [m["text"] for m in r.json()]
    assert "alice msg" in texts
    assert "bob msg" not in texts


def test_non_member_cannot_post_or_read(client):
    register(client, "alice")
    register(client, "bob")
    gid = create_group(client, "alice", "closed")
    r = client.post(
        "/api/messages",
        json={"group_id": gid, "text": "intruder"},
        headers=auth_headers(client, "bob"),
    )
    assert r.status_code == 403
    assert (
        client.get(
            "/api/messages", params={"group_id": gid}, headers=auth_headers(client, "bob")
        ).status_code
        == 403
    )


def test_non_member_cannot_forward_into_group(client):
    register(client, "alice")
    register(client, "bob")
    gid = create_group(client, "alice", "closed")
    other = create_group(client, "bob", "other")
    m = _send_group(client, "bob", "src", other)
    r = client.post(
        f"/api/messages/{m['id']}/forward",
        json={"group_id": gid},
        headers=auth_headers(client, "bob"),
    )
    assert r.status_code == 403


def test_empty_text_rejected(client):
    register(client, "alice")
    gid = _gid_for(client, "alice")
    assert (
        client.post(
            "/api/messages",
            json={"group_id": gid, "text": "   "},
            headers=auth_headers(client, "alice"),
        ).status_code
        == 400
    )


def test_deleted_visible_to_direct_author_only(client):
    register(client, "alice")
    register(client, "bob")
    dm = client.post(
        "/api/directs", json={"username": "bob"}, headers=auth_headers(client, "alice")
    ).json()
    m = _send_group(client, "alice", "secret", dm["id"])
    client.delete(f"/api/messages/{m['id']}", headers=auth_headers(client, "alice"))
    author_list = client.get(
        "/api/messages", params={"group_id": dm["id"]}, headers=auth_headers(client, "alice")
    ).json()
    peer_list = client.get(
        "/api/messages", params={"group_id": dm["id"]}, headers=auth_headers(client, "bob")
    ).json()
    assert any(x["id"] == m["id"] for x in author_list)
    assert not any(x["id"] == m["id"] for x in peer_list)


def test_blocked_author_hidden_in_search(client):
    register(client, "alice")
    register(client, "bob")
    gid = create_group(client, "alice", "pub", members=["bob"])
    _send_group(client, "bob", "throwaway needle", gid)
    client.post("/api/users/bob/block", headers=auth_headers(client, "alice"))
    r = client.get(
        "/api/messages/search", params={"q": "needle"}, headers=auth_headers(client, "alice")
    )
    assert all("needle" not in m["text"] for m in r.json())


def test_search_forbidden_group(client):
    register(client, "alice")
    register(client, "bob")
    gid = create_group(client, "alice", "closed")
    _send_group(client, "alice", "needle", gid)
    r = client.get(
        "/api/messages/search",
        params={"q": "needle", "group_id": gid},
        headers=auth_headers(client, "bob"),
    )
    assert r.status_code == 403


def test_history_forbidden_for_non_member(client):
    register(client, "alice")
    register(client, "bob")
    gid = create_group(client, "alice", "closed")
    m = _send_group(client, "alice", "v1", gid)
    assert (
        client.get(
            f"/api/messages/{m['id']}/history", headers=auth_headers(client, "bob")
        ).status_code
        == 403
    )
