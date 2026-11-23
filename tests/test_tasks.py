from tests.conftest import register_and_login


def test_create_task_sets_owner_from_token(client, auth_headers):
    r = client.post("/tasks", json={"title": "Moje zadanie", "priority": 2}, headers=auth_headers)
    assert r.status_code == 201
    me = client.get("/users/me", headers=auth_headers).json()
    assert r.json()["user_id"] == me["id"]


def test_client_cannot_set_user_id(client):
    h1 = register_and_login(client, "u1@example.com")
    h2 = register_and_login(client, "u2@example.com")
    u2_id = client.get("/users/me", headers=h2).json()["id"]
    r = client.post("/tasks", json={"title": "Podstep", "user_id": u2_id}, headers=h1)
    assert r.status_code == 201
    assert r.json()["user_id"] != u2_id


def test_tasks_are_scoped_to_current_user(client):
    h1 = register_and_login(client, "u1@example.com")
    h2 = register_and_login(client, "u2@example.com")
    client.post("/tasks", json={"title": "Zadanie u1"}, headers=h1)
    client.post("/tasks", json={"title": "Zadanie u2"}, headers=h2)

    r = client.get("/tasks", headers=h1)
    assert r.status_code == 200
    assert [t["title"] for t in r.json()] == ["Zadanie u1"]


def test_foreign_task_update_and_delete_is_403(client):
    h1 = register_and_login(client, "u1@example.com")
    h2 = register_and_login(client, "u2@example.com")
    task_id = client.post("/tasks", json={"title": "Zadanie u1"}, headers=h1).json()["id"]

    r = client.put(f"/tasks/{task_id}",
                   json={"title": "Hack", "completed": True, "priority": 1}, headers=h2)
    assert r.status_code == 403
    assert client.delete(f"/tasks/{task_id}", headers=h2).status_code == 403


def test_owner_can_delete_task_204(client, auth_headers):
    task_id = client.post("/tasks", json={"title": "Do usuniecia"}, headers=auth_headers).json()["id"]
    assert client.delete(f"/tasks/{task_id}", headers=auth_headers).status_code == 204


def test_missing_task_is_404(client, auth_headers):
    assert client.delete("/tasks/9999", headers=auth_headers).status_code == 404


def test_invalid_priority_is_422(client, auth_headers):
    r = client.post("/tasks", json={"title": "Zadanie", "priority": 9}, headers=auth_headers)
    assert r.status_code == 422


def test_health_is_public(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}