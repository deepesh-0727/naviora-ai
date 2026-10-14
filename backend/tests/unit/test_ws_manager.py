import asyncio
import pytest

from app.services.ws_manager import WebSocketManager


class SharedBroker:
    def __init__(self):
        self.subscribers: dict[str, list[asyncio.Queue[str]]] = {}


class BrokerPubSub:
    def __init__(self, broker: SharedBroker):
        self.broker = broker
        self.channels: dict[str, asyncio.Queue[str]] = {}

    async def subscribe(self, channel: str):
        queue: asyncio.Queue[str] = asyncio.Queue()
        self.channels[channel] = queue
        self.broker.subscribers.setdefault(channel, []).append(queue)

    async def unsubscribe(self, channel: str):
        queue = self.channels.pop(channel, None)
        if queue:
            self.broker.subscribers[channel].remove(queue)

    async def get_message(self, ignore_subscribe_messages: bool = True, timeout: float = 1.0):
        try:
            data = await asyncio.wait_for(self.channels["ws:broadcast"].get(), timeout)
        except asyncio.TimeoutError:
            return None
        return {"type": "message", "data": data}

    async def aclose(self):
        for channel in list(self.channels):
            await self.unsubscribe(channel)


class BrokerRedis:
    def __init__(self, broker: SharedBroker):
        self.broker = broker
        self.closed = False

    async def ping(self):
        return True

    def pubsub(self):
        return BrokerPubSub(self.broker)

    async def publish(self, channel: str, payload: str):
        for queue in list(self.broker.subscribers.get(channel, [])):
            await queue.put(payload)

    async def aclose(self):
        self.closed = True


class FakeWebSocket:
    def __init__(self):
        self.messages: list[dict] = []
        self.accepted = False
        self.closed = False

    async def accept(self):
        self.accepted = True

    async def send_json(self, message: dict):
        self.messages.append(message)

    async def close(self, code: int = 1000, reason: str | None = None):
        self.closed = True


async def wait_for_messages(socket: FakeWebSocket, count: int):
    for _ in range(100):
        if len(socket.messages) >= count:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"Expected {count} WebSocket messages, received {len(socket.messages)}")


@pytest.mark.asyncio
async def test_broadcast_fans_out_between_two_manager_instances():
    broker = SharedBroker()
    first = WebSocketManager(redis=BrokerRedis(broker))
    second = WebSocketManager(redis=BrokerRedis(broker))
    first_socket = FakeWebSocket()
    second_socket = FakeWebSocket()

    await first.start()
    await second.start()
    try:
        await first.connect(first_socket, "u1", {"role": "doctor", "staff_id": 42})
        await second.connect(second_socket, "u2", {"role": "doctor", "staff_id": 42})
        message = {"event": "queue_update", "data": {"position": 3}}
        await first.broadcast("doctor:42", message)
        await wait_for_messages(second_socket, 1)

        assert first_socket.messages == [message]
        assert second_socket.messages == [message]
    finally:
        await first.shutdown()
        await second.shutdown()


@pytest.mark.asyncio
async def test_broadcast_requires_started_redis_listener():
    manager = WebSocketManager(redis=BrokerRedis(SharedBroker()))
    with pytest.raises(RuntimeError, match="not started"):
        await manager.broadcast("emergency", {"event": "emergency_new"})
    await manager.shutdown()


@pytest.mark.asyncio
async def test_broadcast_event_uses_timestamped_envelope_and_failure_is_non_blocking():
    manager = WebSocketManager(redis=BrokerRedis(SharedBroker()))
    socket = FakeWebSocket()
    await manager.start()
    await manager.connect(socket, "u1", {"role": "emergency"})
    try:
        assert await manager.broadcast_event("emergency", "emergency_new", {"id": 3})
        payload = socket.messages[0]
        assert payload["event"] == "emergency_new"
        assert payload["timestamp"]
        assert payload["data"] == {"id": 3}
    finally:
        await manager.shutdown()

    unavailable = WebSocketManager(redis=BrokerRedis(SharedBroker()))
    assert not await unavailable.broadcast_event("emergency", "emergency_new", {"id": 4})
    await unavailable.shutdown()


@pytest.mark.asyncio
async def test_start_fails_clearly_when_redis_is_unavailable():
    class UnavailableRedis(BrokerRedis):
        async def ping(self):
            raise OSError("connection refused")

    manager = WebSocketManager(redis=UnavailableRedis(SharedBroker()))
    with pytest.raises(RuntimeError, match="Redis pub/sub is unavailable"):
        await manager.start()
    await manager.shutdown()


@pytest.mark.asyncio
async def test_connection_joins_claim_rooms_and_rejects_unauthorized_rooms():
    manager = WebSocketManager(redis=BrokerRedis(SharedBroker()))
    socket = FakeWebSocket()
    await manager.connect(socket, "user-1", {"role": "patient", "patient_id": 15})
    try:
        assert socket.accepted
        assert socket in manager.rooms["patient:15"]
        assert await manager.join_room(socket, "patient:15")
        assert not await manager.join_room(socket, "admin")
    finally:
        await manager.disconnect(socket, "user-1")
        assert "patient:15" not in manager.rooms
        await manager.shutdown()


@pytest.mark.asyncio
async def test_leave_room_and_heartbeat_pong_keep_connection_alive():
    manager = WebSocketManager(redis=BrokerRedis(SharedBroker()))
    manager.HEARTBEAT_INTERVAL = 0.01
    manager.HEARTBEAT_TIMEOUT = 0.1
    socket = FakeWebSocket()
    await manager.connect(socket, "doctor-user", {"role": "doctor", "staff_id": 8})
    try:
        await manager.leave_room(socket, "doctor:8")
        assert "doctor:8" not in manager.rooms
        await wait_for_messages(socket, 1)
        assert socket.messages[0] == {"action": "ping"}
        manager.handle_pong(socket)
        await asyncio.sleep(0.02)
        assert socket in manager.active_connections["doctor-user"]
    finally:
        await manager.shutdown()


@pytest.mark.asyncio
async def test_heartbeat_closes_connection_without_pong():
    manager = WebSocketManager(redis=BrokerRedis(SharedBroker()))
    manager.HEARTBEAT_INTERVAL = 0.01
    manager.HEARTBEAT_TIMEOUT = 0.02
    socket = FakeWebSocket()
    await manager.connect(socket, "doctor-user", {"role": "doctor", "staff_id": 8})
    try:
        for _ in range(100):
            if socket.closed:
                break
            await asyncio.sleep(0.01)
        assert socket.closed
        assert "doctor-user" not in manager.active_connections
    finally:
        await manager.shutdown()


@pytest.mark.asyncio
async def test_personal_messages_and_global_broadcast_use_registered_rooms():
    manager = WebSocketManager(redis=BrokerRedis(SharedBroker()))
    socket = FakeWebSocket()
    await manager.start()
    await manager.connect(socket, "user-1", {"role": "doctor", "staff_id": 8})
    try:
        await manager.send_personal_message({"type": "rtc_offer"}, "user-1")
        await manager.broadcast_to_room({"event": "queue_update"}, "doctor:8")
        await manager.broadcast_global({"event": "queue_update"})
        await wait_for_messages(socket, 3)
        assert socket.messages == [
            {"type": "rtc_offer"},
            {"event": "queue_update"},
            {"event": "queue_update"},
        ]
    finally:
        await manager.shutdown()


def test_recent_message_registry_deduplicates_deliveries():
    manager = WebSocketManager(redis=BrokerRedis(SharedBroker()))
    assert not manager._was_delivered("message-1")
    assert manager._was_delivered("message-1")
