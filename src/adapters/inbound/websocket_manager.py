import json
from typing import List
from fastapi import WebSocket


class ConnectionManager:
    """Manages active WebSocket connections for real-time telemetry streaming."""

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        """Broadcast telemetry data payload to all connected clients."""
        serialized_msg = json.dumps(message)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(serialized_msg)
            except Exception:
                disconnected.append(connection)

        # Cleanup inactive connections
        for conn in disconnected:
            self.disconnect(conn)


# Singleton instance of the connection manager
manager = ConnectionManager()
