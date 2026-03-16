from __future__ import annotations

from utils import hash_password


def test_signup_success(client, monkeypatch):
    created = {}

    monkeypatch.setattr("controllers.auth.auth_model.count_users_by_email", lambda email: 0)
    monkeypatch.setattr("controllers.auth.auth_model.count_users_by_nickname", lambda nickname: 0)

    def _create_user(email, password_hash, nickname, profile_image):
        created.update(
            {
                "email": email,
                "password_hash": password_hash,
                "nickname": nickname,
                "profile_image": profile_image,
            }
        )

    monkeypatch.setattr("controllers.auth.auth_model.create_user", _create_user)

    response = client.post(
        "/v1/auth/signup",
        json={
            "email": "user@example.com",
            "password": "Qa!12345Aa",
            "nickname": "사용자1",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "SIGNUP_SUCCESS"
    assert created["email"] == "user@example.com"
    assert created["nickname"] == "사용자1"
    assert created["password_hash"].startswith("$2")


def test_signup_duplicate_email_returns_409(client, monkeypatch):
    monkeypatch.setattr("controllers.auth.auth_model.count_users_by_email", lambda email: 1)

    response = client.post(
        "/v1/auth/signup",
        json={
            "email": "duplicate@example.com",
            "password": "Qa!12345Aa",
            "nickname": "중복닉네임",
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "ALREADY_EXIST_EMAIL"


def test_login_success_sets_session_cookie(client, monkeypatch):
    monkeypatch.setattr(
        "controllers.auth.auth_model.get_user_by_email",
        lambda email: {
            "userId": 7,
            "email": email,
            "nickname": "tester",
            "profileimage": None,
            "password": hash_password("Qa!12345Aa"),
        },
    )

    session_calls = {}

    def _create_session(session_id, user_email):
        session_calls["session_id"] = session_id
        session_calls["user_email"] = user_email

    monkeypatch.setattr("controllers.auth.auth_model.create_session", _create_session)

    response = client.post(
        "/v1/auth/login",
        json={"email": "user@example.com", "password": "Qa!12345Aa"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "LOGIN_SUCCESS"
    assert body["data"]["userId"] == 7
    assert session_calls["user_email"] == "user@example.com"
    assert "session_id=" in response.headers.get("set-cookie", "")


def test_login_failure_returns_400(client, monkeypatch):
    monkeypatch.setattr("controllers.auth.auth_model.get_user_by_email", lambda email: None)

    response = client.post(
        "/v1/auth/login",
        json={"email": "missing@example.com", "password": "Qa!12345Aa"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "LOGIN_FAILED"


def test_me_requires_valid_session(client, monkeypatch):
    monkeypatch.setattr("dependencies.auth_model.get_user_email_by_session_id", lambda session_id: None)

    response = client.get("/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "LOGIN_REQUIRED"


def test_me_returns_current_user_with_valid_session(client, monkeypatch):
    monkeypatch.setattr("dependencies.auth_model.get_user_email_by_session_id", lambda session_id: "user@example.com")
    monkeypatch.setattr(
        "dependencies.user_model.get_user_by_email",
        lambda email: {
            "userId": 9,
            "email": email,
            "nickname": "session-user",
            "profileimage": None,
        },
    )

    response = client.get("/v1/auth/me", cookies={"session_id": "valid-session"})

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "GET_MY_INFO_SUCCESS"
    assert body["data"]["email"] == "user@example.com"
