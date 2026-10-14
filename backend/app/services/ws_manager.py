"""Redis-backed WebSocket fan-out with an instance-local connection registry."""

import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict
from contextlib import suppress
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect
from redis.asyncio import Redis
from redis.asyncio.client import PubSub

from app.core.config import settings

logger = logging.getLogger(__name__)


class WebSocketManager:
    CHANNEL = "ws:broadcast"
    HEARTBEAT_INTERVAL = 30.0
    HEARTBEAT_TIMEOUT = 10.0
    DEDUPE_TTL = 60.0

    def __init__(self, redis: Redis | None = None) -> None:
        if redis is None and not settings.REDIS_URL.strip():
            raise RuntimeError("WebSocket broadcasts require REDIS_URL to be configured.")
        self._redis_injected = redis is not None
        self.redis: Redis = redis or Redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.rooms: defaultdict[str, set[WebSocket]] = defaultdict(set)
        self.active_connections: defaultdict[str, set[WebSocket]] = defaultdict(set)
        self._user_rooms: dict[WebSocket, set[str]] = {}
        self._claims: dict[WebSocket, dict[str, object]] = {}
        self._pong_events: dict[WebSocket, asyncio.Event] = {}
        self._heartbeat_tasks: dict[WebSocket, asyncio.Task[None]] = {}
        self._pubsub: PubSub | None = None
        self._listener_task: asyncio.Task[None] | None = None
        self._recent_messages: dict[str, float] = {}

    async def start(self) -> None:
        """Verify Redis and subscribe before accepting WebSocket traffic."""
        if self._listener_task and not self._listener_task.done():
            return
        if not settings.REDIS_URL.strip() and isinstance(self.redis, Redis):
            raise RuntimeError("WebSocket broadcasts require REDIS_URL to be configured.")
        try:
            await self.redis.ping()
            self._pubsub = self.redis.pubsub()
            await self._pubsub.subscribe(self.CHANNEL)
        except Exception as exc:
            if self._pubsub is not None:
                with suppress(Exception):
                    await self._pubsub.aclose()
                self._pubsub = None
            raise RuntimeError("WebSocket Redis pub/sub is unavailable; configure Redis before startup.") from exc
        self._listener_task = asyncio.create_task(self._listen(), name="websocket-redis-listener")
        logger.info("WebSocket Redis listener subscribed to %s", self.CHANNEL)

    async def shutdown(self) -> None:
        """Stop Redis listening and close this instance's active sockets."""
        if self._listener_task:
            self._listener_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._listener_task
            self._listener_task = None
        if self._pubsub is not None:
            with suppress(Exception):
                await self._pubsub.unsubscribe(self.CHANNEL)
                await self._pubsub.aclose()
            self._pubsub = None
        for websocket in list(self._user_rooms):
            await self._remove_connection(websocket, close=True, close_reason="Server shutting down")
        await self.redis.aclose()
        if not self._redis_injected:
            self.redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def _listen(self) -> None:
        """Receive Redis messages and deliver messages from other instances."""
        while True:
            try:
                item = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if item is None:
                    continue
                raw_data = item.get("data")
                if not isinstance(raw_data, str):
                    continue
                payload = json.loads(raw_data)
                if not isinstance(payload, dict):
                    continue
                message_id = payload.get("id")
                room = payload.get("room")
                message = payload.get("message")
                origin = payload.get("origin")
                if not all(isinstance(value, str) and value for value in (message_id, room, origin)):
                    continue
                if not isinstance(message, dict):
                    continue
                if origin == self._instance_id:
                    continue
                if self._was_delivered(message_id):
                    continue
                await self._deliver_room(room, message)
            except asyncio.CancelledError:
                raise
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                logger.warning("Ignoring malformed WebSocket Redis message: %s", exc)
            except Exception:
                logger.exception("WebSocket Redis listener encountered an error")
                await asyncio.sleep(0.25)

    @property
    def _instance_id(self) -> str:
        if not hasattr(self, "_id"):
            self._id = str(uuid.uuid4())
        return self._id

    def _was_delivered(self, message_id: str) -> bool:
        now = time.monotonic()
        expired = [key for key, expiry in self._recent_messages.items() if expiry <= now]
        for key in expired:
            self._recent_messages.pop(key, None)
        if message_id in self._recent_messages:
            return True
        self._recent_messages[message_id] = now + self.DEDUPE_TTL
        return False

    async def broadcast(self, room: str, message: dict[str, object]) -> None:
        """Publish to Redis and deliver once to this instance's room members."""
        if not self._listener_task or self._listener_task.done():
            raise RuntimeError("WebSocketManager is not started; Redis pub/sub is required for broadcast.")
        message_id = str(uuid.uuid4())
        payload = json.dumps({"id": message_id, "origin": self._instance_id, "room": room, "message": message})
        await self.redis.publish(self.CHANNEL, payload)
        self._was_delivered(message_id)
        await self._deliver_room(room, message)

    async def broadcast_event(self, room: str, event: str, data: dict[str, object]) -> bool:
        """Send a standard event envelope; Redis failure never blocks its API caller."""
        payload = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        try:
            await self.broadcast(room, payload)
            return True
        except Exception:
            logger.exception("Unable to publish WebSocket event %s to room %s", event, room)
            return False

    async def _deliver_room(self, room: str, message: dict[str, object]) -> None:
        for websocket in list(self.rooms.get(room, set())):
            try:
                await websocket.send_json(message)
            except (WebSocketDisconnect, RuntimeError, OSError):
                logger.info("Removing disconnected WebSocket from room %s", room)
                await self._remove_connection(websocket)
            except Exception:
                logger.exception("Unable to deliver WebSocket event to room %s", room)
                await self._remove_connection(websocket)

    async def connect(self, websocket: WebSocket, user_id: str, claims: dict[str, object] | None = None) -> None:
        """Accept an authenticated socket and add its role-specific rooms."""
        await websocket.accept()
        self.active_connections[user_id].add(websocket)
        self._claims[websocket] = claims or {}
        self._user_rooms[websocket] = set()
        user_room = f"user:{user_id}"
        self.rooms[user_room].add(websocket)
        self._user_rooms[websocket].add(user_room)
        for room in self._rooms_for_claims(user_id, self._claims[websocket]):
            self.rooms[room].add(websocket)
            self._user_rooms[websocket].add(room)
        pong_event = asyncio.Event()
        self._pong_events[websocket] = pong_event
        self._heartbeat_tasks[websocket] = asyncio.create_task(
            self._heartbeat(websocket, pong_event), name=f"websocket-heartbeat-{user_id}"
        )
        logger.info("User %s connected via WebSocket", user_id)

    @staticmethod
    def _rooms_for_claims(user_id: str, claims: dict[str, object]) -> set[str]:
        role = claims.get("role")
        rooms: set[str] = set()
        if role == "patient":
            rooms.add(f"patient:{claims.get('patient_id') or user_id}")
        elif role == "doctor":
            rooms.add(f"doctor:{claims.get('staff_id') or user_id}")
        elif role == "nurse":
            rooms.add(f"nurse:{claims.get('staff_id') or user_id}")
        elif role in {"doctor", "nurse", "front_desk", "pharmacy", "facilities", "emergency", "staff", "admin", "super_admin"}:
            rooms.add(f"staff:{user_id}")
        ward_id = claims.get("ward_id")
        if role in {"doctor", "nurse", "staff", "admin", "super_admin"} and ward_id:
            rooms.add(f"ward:{ward_id}")
        if role in {"emergency", "doctor", "nurse", "staff", "admin", "super_admin"}:
            rooms.add("emergency")
        if role in {"pharmacy", "staff", "admin", "super_admin"}:
            rooms.add("pharmacy")
        if role in {"facilities", "staff", "admin", "super_admin"}:
            rooms.add("facilities")
        if role in {"admin", "super_admin"}:
            rooms.add("admin")
        if role in {"doctor", "nurse", "front_desk", "staff", "admin", "super_admin"}:
            rooms.add("queue:all")
        return rooms

    @staticmethod
    def _authorized_for_room(room: str, claims: dict[str, object], user_id: str) -> bool:
        role = claims.get("role")
        if room == f"user:{user_id}":
            return str(claims.get("sub") or user_id) == user_id
        if room == f"patient:{claims.get('patient_id') or user_id}":
            return role == "patient"
        if room == f"doctor:{claims.get('staff_id') or user_id}":
            return role == "doctor"
        if room == f"nurse:{claims.get('staff_id') or user_id}":
            return role == "nurse"
        if room == f"staff:{user_id}":
            return role in {"doctor", "nurse", "front_desk", "pharmacy", "facilities", "emergency", "staff", "admin", "super_admin"}
        if room == f"ward:{claims.get('ward_id')}" and claims.get("ward_id"):
            return role in {"doctor", "nurse", "staff", "admin", "super_admin"}
        allowed_roles = {
            "emergency": {"emergency", "doctor", "nurse", "staff", "admin", "super_admin"},
            "pharmacy": {"pharmacy", "staff", "admin", "super_admin"},
            "facilities": {"facilities", "staff", "admin", "super_admin"},
            "admin": {"admin", "super_admin"},
            "queue:all": {"doctor", "nurse", "front_desk", "staff", "admin", "super_admin"},
        }
        return role in allowed_roles.get(room, set())

    async def _heartbeat(self, websocket: WebSocket, pong_event: asyncio.Event) -> None:
        try:
            while True:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                pong_event.clear()
                await websocket.send_json({"action": "ping"})
                await asyncio.wait_for(pong_event.wait(), timeout=self.HEARTBEAT_TIMEOUT)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.info("WebSocket heartbeat failed; closing stale connection")
            await self._remove_connection(websocket, close=True)

    def handle_pong(self, websocket: WebSocket) -> None:
        """Mark a client heartbeat response as received."""
        event = self._pong_events.get(websocket)
        if event:
            event.set()

    async def join_room(self, websocket: WebSocket, room_name: str) -> bool:
        """Join a room only when the authenticated claims authorize it."""
        claims = self._claims.get(websocket)
        user_id = next((key for key, sockets in self.active_connections.items() if websocket in sockets), None)
        if claims is None or user_id is None or not self._authorized_for_room(room_name, claims, user_id):
            return False
        self.rooms[room_name].add(websocket)
        self._user_rooms[websocket].add(room_name)
        return True

    async def leave_room(self, websocket: WebSocket, room_name: str) -> None:
        self.rooms[room_name].discard(websocket)
        if not self.rooms[room_name]:
            self.rooms.pop(room_name, None)
        self._user_rooms.get(websocket, set()).discard(room_name)

    async def _remove_connection(
        self,
        websocket: WebSocket,
        close: bool = False,
        close_reason: str = "WebSocket heartbeat timed out",
    ) -> None:
        for room in self._user_rooms.pop(websocket, set()):
            self.rooms[room].discard(websocket)
            if not self.rooms[room]:
                self.rooms.pop(room, None)
        self._claims.pop(websocket, None)
        self._pong_events.pop(websocket, None)
        current_task = asyncio.current_task()
        heartbeat_task = self._heartbeat_tasks.pop(websocket, None)
        if heartbeat_task and heartbeat_task is not current_task:
            heartbeat_task.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat_task
        for user_id, connections in list(self.active_connections.items()):
            connections.discard(websocket)
            if not connections:
                self.active_connections.pop(user_id, None)
        if close:
            with suppress(Exception):
                await websocket.close(code=1001 if close_reason == "Server shutting down" else 1011, reason=close_reason)

    async def disconnect(self, websocket: WebSocket, user_id: str | None = None) -> None:
        """Remove a socket from every room and user registry."""
        await self._remove_connection(websocket)

    async def send_personal_message(self, message: dict[str, object], user_id: str) -> None:
        """Publish to the user's private room across all backend instances."""
        await self.broadcast_to_room(message, f"user:{user_id}")

    async def broadcast_to_room(self, message: dict[str, object], room_name: str) -> None:
        """Compatibility wrapper that retains existing room broadcast call sites."""
        try:
            await self.broadcast(room_name, message)
        except Exception:
            logger.exception("Unable to publish WebSocket message to room %s", room_name)

    async def broadcast_global(self, message: dict[str, object]) -> None:
        """Broadcast to all clients subscribed to the shared all-queue room."""
        await self.broadcast_to_room(message, "queue:all")


ws_manager = WebSocketManager()
