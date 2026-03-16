from __future__ import annotations


def test_readiness_reflects_database_state(client, monkeypatch):
    monkeypatch.setattr("main.is_db_ready", lambda: False)

    response = client.get("/healthz/ready")

    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"


def test_realtime_health_reflects_redis_state(client, monkeypatch):
    async def _status():
        return {"ready": False, "publisher_ready": False, "subscriber_ready": False}

    monkeypatch.setattr("main.get_redis_status_async", _status)

    response = client.get("/healthz/realtime")

    assert response.status_code == 503
    assert response.json()["status"] == "unready"
