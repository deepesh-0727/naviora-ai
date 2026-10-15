import json

import pytest
from fastapi import WebSocketDisconnect
import fakeredis.aioredis
from unittest.mock import AsyncMock

from app.core.security import create_access_token, create_refresh_token
from app.services import ws_manager
from app.api.v1.endpoints import websocket as websocket_endpoint_module


def _token(user_id="101", role="doctor", **claims):
    return create_access_token(subject=user_id, claims={"role": role, **claims})


def _use_fake_redis(monkeypatch, *, fail_ping=False):
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    if fail_ping:
        async def unavailable():
            raise ConnectionError("dedicated test Redis unavailable")
        monkeypatch.setattr(redis, "ping", unavailable)
    monkeypatch.setattr(websocket_endpoint_module.Redis, "from_url", lambda *args, **kwargs: redis)
    return redis


def _connect(client, url):
    return client.websocket_connect(url, headers={"host": "localhost"})


def test_websocket_rejects_invalid_and_refresh_tokens(client):
    for token in ("invalid-token", create_refresh_token("101")):
        with pytest.raises(WebSocketDisconnect) as closed:
            with _connect(client, f"/api/v1/stream?token={token}"):
                pass
        assert closed.value.code == 4003


def test_websocket_rejects_non_numeric_user_id(client):
    token = _token(user_id="patient-101", role="patient")
    with pytest.raises(WebSocketDisconnect) as closed:
        with _connect(client, f"/api/v1/stream?token={token}"):
            pass
    assert closed.value.code == 4003


def test_doctor_socket_receives_pong_and_joins_authorized_queue_room(client, monkeypatch):
    _use_fake_redis(monkeypatch)
    token = _token(staff_id=42)
    with _connect(client, f"/api/v1/stream?token={token}&session_id=queue-test") as socket:
        socket.send_json({"action": "ping"})
        assert socket.receive_json() == {"action": "pong"}
        socket.send_json({"action": "join_room", "room": "queue:all"})
        assert socket.receive_json() == {"action": "joined_room", "room": "queue:all"}
        assert any(ws_manager.ws_manager.rooms.get("doctor:42", set()))

    assert "doctor:42" not in ws_manager.ws_manager.rooms


def test_patient_cannot_join_admin_room_and_can_leave_own_room(client, monkeypatch):
    _use_fake_redis(monkeypatch)
    token = _token(user_id="102", role="patient", patient_id=77)

    with _connect(client, f"/api/v1/stream?token={token}") as socket:
        socket.send_json({"action": "join_room", "room": "admin"})
        assert socket.receive_json() == {"type": "error", "message": "Not authorized to join room"}
        socket.send_json({"action": "leave_room", "room": "patient:77"})
        assert socket.receive_json() == {"action": "left_room", "room": "patient:77"}


def test_websocket_closes_with_retry_code_when_session_redis_is_unavailable(client, monkeypatch):
    _use_fake_redis(monkeypatch, fail_ping=True)
    token = _token()
    with pytest.raises(WebSocketDisconnect) as closed:
        with _connect(client, f"/api/v1/stream?token={token}"):
            pass
    assert closed.value.code == 1013


def test_rtc_signaling_is_forwarded_to_target_user(client, monkeypatch):
    _use_fake_redis(monkeypatch)
    sender_token = _token(user_id="103", role="doctor", staff_id=42)
    send_to_user = AsyncMock()
    monkeypatch.setattr(ws_manager.ws_manager, "send_personal_message", send_to_user)

    with _connect(client, f"/api/v1/stream?token={sender_token}") as sender:
        packet = {"candidate": "candidate-1"}
        sender.send_json({"action": "rtc_candidate", "target_id": "104", "data": packet})
        sender.send_json({"action": "ping"})
        assert sender.receive_json() == {"action": "pong"}
        assert send_to_user.await_args.args == ({"type": "rtc_candidate", "sender_id": "103", "data": packet}, "104")


@pytest.mark.asyncio
async def test_session_context_load_adds_identity_and_save_round_trips():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    key = "test:session:123:session-a"
    await redis.set(key, json.dumps({"topic": "follow-up"}))

    loaded = await websocket_endpoint_module._load_session_context(redis, key, "123", "session-a")
    empty = await websocket_endpoint_module._load_session_context(redis, "test:missing", "123", "session-b")
    await websocket_endpoint_module._save_session_context(redis, key, "123", "session-a")
    saved = json.loads(await redis.get(key))

    assert loaded == {"topic": "follow-up", "session_id": "session-a", "user_id": 123}
    assert empty == {"session_id": "session-b", "user_id": 123}
    assert saved == {"session_id": "session-a", "user_id": 123}
    await redis.aclose()
