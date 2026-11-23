def test_register(client):
    r = client.post("/auth/register", json={
        "email": "a@example.com", "name": "Anna", "password": "Haslo123!"
    })
    assert r.status_code == 201
    assert "password" not in r.json()
    assert "hashed_password" not in r.json()


def test_duplicate_email(client):
    payload = {"email": "a@example.com", "name": "Anna", "password": "Haslo123!"}
    assert client.post("/auth/register", json=payload).status_code == 201
    assert client.post("/auth/register", json=payload).status_code == 409


def test_short_password_is_422(client):
    r = client.post("/auth/register", json={
        "email": "b@example.com", "name": "Bartek", "password": "123"
    })
    assert r.status_code == 422


def test_login_and_me(client):
    client.post("/auth/register", json={
        "email": "c@example.com", "name": "Celina", "password": "Haslo123!"
    })
    r = client.post("/auth/login", data={"username": "c@example.com", "password": "Haslo123!"})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    token = r.json()["access_token"]

    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "c@example.com"


def test_login_wrong_password_is_401(client):
    client.post("/auth/register", json={
        "email": "d@example.com", "name": "Dawid", "password": "Haslo123!"
    })
    r = client.post("/auth/login", data={"username": "d@example.com", "password": "zlehaslo1"})
    assert r.status_code == 401


def test_protected_without_token(client):
    r = client.get("/users/me")
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"