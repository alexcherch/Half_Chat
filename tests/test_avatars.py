import io

from tests.conftest import PNG_1PX, auth_headers, create_group, register


def _upload(client, username, content, content_type):
    return client.put(
        "/api/users/me/avatar",
        files={"file": ("a.bin", io.BytesIO(content), content_type)},
        headers=auth_headers(client, username),
    )


def register_group(client):
    register(client, "alice")
    return create_group(client, "alice", "av")


def test_avatar_oversize(client):
    register(client, "alice")
    big = io.BytesIO(PNG_1PX * (5 * 1024 * 1024 // len(PNG_1PX) + 1))  # > 5 МБ
    r = client.put(
        "/api/users/me/avatar",
        files={"file": ("big.png", big, "image/png")},
        headers=auth_headers(client, "alice"),
    )
    assert r.status_code == 413


def test_avatar_bad_content_type(client):
    register(client, "alice")
    assert _upload(client, "alice", b"hello", "text/plain").status_code == 400


def test_avatar_content_sniffed(client):
    register(client, "alice")
    assert _upload(client, "alice", b"GIF-sniffed-but-png", "image/png").status_code == 400


def test_avatar_reupload_replaces(client):
    register(client, "alice")
    first = client.put(
        "/api/users/me/avatar",
        files={"file": ("a.png", io.BytesIO(PNG_1PX), "image/png")},
        headers=auth_headers(client, "alice"),
    ).json()["avatar_url"]
    second = client.put(
        "/api/users/me/avatar",
        files={"file": ("a.png", io.BytesIO(PNG_1PX), "image/png")},
        headers=auth_headers(client, "alice"),
    ).json()["avatar_url"]
    assert first == second  # один файл u{id}{ext}


def test_group_avatar_invalid(client):
    gid = register_group(client)
    register(client, "bob")
    r = client.post(
        f"/api/groups/{gid}/avatar",
        files={"file": ("g.png", io.BytesIO(b"junk"), "image/png")},
        headers=auth_headers(client, "alice"),
    )
    assert r.status_code == 400
