import asyncio
import pytest
from redis.asyncio import Redis

from app.services.ws_manager import WebSocketManager


class ConnectedSocket:
    def __init__(self):
        self.messages = []
        self.accepted = False

    async def accept(self):
        self.accepted = True

    async def send_json(self, message):
        self.messages.append(message)

    async def close(self, code=1000, reason=None):
        return None


@pytest.mark.asyncio
async def test_realtime_fanout_reaches_second_manager_through_test_redis(configured_test_redis_url):
    redis_url = configured_test_redis_url
    first = WebSocketManager(redis=Redis.from_url(redis_url, decode_responses=True))
    second = WebSocketManager(redis=Redis.from_url(redis_url, decode_responses=True))
    first_socket = ConnectedSocket()
    second_socket = ConnectedSocket()
    await first.start()
    await second.start()
    try:
        await first.connect(first_socket, "doctor-one", {"role": "doctor", "staff_id": 55})
        await second.connect(second_socket, "doctor-two", {"role": "doctor", "staff_id": 55})
        payload = {"position": 4, "appointment_id": 901}
        assert await first.broadcast_event("doctor:55", "queue_update", payload)

        for _ in range(100):
            if second_socket.messages:
                break
            await asyncio.sleep(0.01)

        assert first_socket.messages[0]["event"] == "queue_update"
        assert first_socket.messages[0]["data"] == payload
        assert second_socket.messages[0]["event"] == "queue_update"
        assert second_socket.messages[0]["data"] == payload
    finally:
        await first.shutdown()
        await second.shutdown()
