from typing import Dict, Set
from fastapi import WebSocket
import json


class ChatConnectionManager:
    """Manages active WebSocket connections per chat group."""

    def __init__(self):
        # group_id -> set of websockets
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, group_id: int):
        await websocket.accept()
        if group_id not in self.active_connections:
            self.active_connections[group_id] = set()
        self.active_connections[group_id].add(websocket)

    def disconnect(self, websocket: WebSocket, group_id: int):
        if group_id in self.active_connections:
            self.active_connections[group_id].discard(websocket)
            if not self.active_connections[group_id]:
                del self.active_connections[group_id]

    async def broadcast(self, group_id: int, message: dict):
        if group_id not in self.active_connections:
            return
        dead = set()
        for connection in self.active_connections[group_id]:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                dead.add(connection)
        for connection in dead:
            self.active_connections[group_id].discard(connection)


manager = ChatConnectionManager()
