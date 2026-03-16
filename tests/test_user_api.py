from __future__ import annotations

from utils import hash_password


def test_update_user_duplicate_nickname_returns_409(client, override_current_user, auth_user, monkeypatch):
    override_current_user(auth_user)
    monkeypatch.setattr("controllers.user.user_model.get_user_by_id", lambda user_id: dict(auth_user))
    monkeypatch.setattr("controllers.user.user_model.count_users_by_nickname_excluding_user", lambda nickname, user_id: 1)

    response = client.patch(f"/v1/users/{auth_user['userId']}", json={"nickname": "중복닉네임"})

    assert response.status_code == 409
    assert response.json()["code"] == "ALREADY_EXIST_NICKNAME"


def test_change_password_requires_matching_current_password(client, override_current_user, auth_user, monkeypatch):
    override_current_user(auth_user)
    monkeypatch.setattr(
        "controllers.user.user_model.get_user_by_id",
        lambda user_id: {**auth_user, "password": hash_password("Current!123")},
    )

    response = client.patch(
        f"/v1/users/{auth_user['userId']}/password",
        json={"currentPassword": "Wrong!123", "newPassword": "Next!123Aa"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CURRENT_PASSWORD"


def test_delete_user_hard_delete_success(client, override_current_user, auth_user, monkeypatch):
    override_current_user(auth_user)
    deleted = {}

    def _hard_delete(user_id, user_email):
        deleted["user_id"] = user_id
        deleted["user_email"] = user_email

    monkeypatch.setattr("controllers.user.user_model.hard_delete_user", _hard_delete)

    response = client.delete("/v1/users/me")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "DELETE_USER_SUCCESS"
    assert deleted == {"user_id": 1, "user_email": "tester@example.com"}
