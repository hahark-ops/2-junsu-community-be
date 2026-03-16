from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import main
from dependencies import get_current_user


@pytest.fixture
def auth_user():
    return {
        "userId": 1,
        "email": "tester@example.com",
        "nickname": "tester",
        "profileimage": "http://example.com/profile.png",
        "password": "hashed-password",
    }


@pytest.fixture
def client(monkeypatch):
    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(main, "start_room_event_subscriber", _noop)
    monkeypatch.setattr(main, "stop_room_event_subscriber", _noop)
    main.app.dependency_overrides.clear()

    with TestClient(main.app) as test_client:
        yield test_client

    main.app.dependency_overrides.clear()


@pytest.fixture
def override_current_user():
    def _apply(user: dict):
        main.app.dependency_overrides[get_current_user] = lambda: user

    yield _apply
    main.app.dependency_overrides.pop(get_current_user, None)
