import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        # Maps user_id to their active websocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Maps room names (e.g., department ID, emergency ID) to sets of websockets
        self.room_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"User {user_id} connected via WebSocket. Active sessions: {len(self.active_connections[user_id])}")

    async def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected from WebSocket.")

    async def join_room(self, websocket: WebSocket, room_name: str):
        if room_name not in self.room_connections:
            self.room_connections[room_name] = set()
        self.room_connections[room_name].add(websocket)
        logger.info(f"WebSocket joined room: {room_name}")

    async def leave_room(self, websocket: WebSocket, room_name: str):
        if room_name in self.room_connections:
            self.room_connections[room_name].discard(websocket)
            if not self.room_connections[room_name]:
                del self.room_connections[room_name]
        logger.info(f"WebSocket left room: {room_name}")

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")

    async def broadcast_to_room(self, message: dict, room_name: str):
        if room_name in self.room_connections:
            for connection in list(self.room_connections[room_name]):
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to room {room_name}: {e}")
                    # Auto clean up dead connections
                    self.room_connections[room_name].discard(connection)

    async def broadcast_global(self, message: dict):
        for user_id, connections in self.active_connections.items():
            for connection in list(connections):
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending global broadcast to user {user_id}: {e}")

ws_manager = WebSocketManager()
