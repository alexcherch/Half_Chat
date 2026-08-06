from typing import Dict, List

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
        self.user_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, group_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.setdefault(group_id, []).append(websocket)

    def disconnect(self, group_id: int, websocket: WebSocket) -> None:
        connections = self.active_connections.get(group_id, [])
        if websocket in connections:
            connections.remove(websocket)
        if not connections:
            self.active_connections.pop(group_id, None)

    async def connect_user(self, username: str, websocket: WebSocket) -> None:
        self.user_connections.setdefault(username, []).append(websocket)

    def disconnect_user(self, username: str, websocket: WebSocket) -> None:
        connections = self.user_connections.get(username, [])
        if websocket in connections:
            connections.remove(websocket)
        if not connections:
            self.user_connections.pop(username, None)

    async def broadcast(self, group_id: int, payload: dict) -> None:
        connections = list(self.active_connections.get(group_id, []))
        for websocket in connections:
            try:
                await websocket.send_json(payload)
            except Exception:
                self.disconnect(group_id, websocket)

    async def send_to_user(self, username: str, payload: dict) -> None:
        connections = list(self.user_connections.get(username, []))
        for websocket in connections:
            try:
                await websocket.send_json(payload)
            except Exception:
                self.disconnect_user(username, websocket)

    def is_online(self, username: str) -> bool:
        return bool(self.user_connections.get(username))


manager = ConnectionManager()
