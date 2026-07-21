import asyncio
import json
import logging
import os

from fastapi import WebSocket

import redis.asyncio as aioredis

logger = logging.getLogger("WebSocketManager")


class ConnectionManager:
    """Manages active WebSocket connections and integrates Redis Pub/Sub for scalability."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()
        self.redis_client = None

        redis_url = os.getenv("REDIS_URL")
        if redis_url and aioredis is not None:
            try:
                self.redis_client = aioredis.from_url(redis_url)
                logger.info(f"WebSocketManager configured with Redis Pub/Sub at: {redis_url}")
            except Exception as exc:
                logger.error(f"Failed to initialize Redis connection: {exc}. Falling back to local in-memory mode.")
        elif redis_url and aioredis is None:
            logger.warning("REDIS_URL set but redis package is not installed. Falling back to local in-memory mode.")
        else:
            logger.info("WebSocketManager initialized in Local In-Memory fallback mode (no REDIS_URL provided).")

    async def connect(self, websocket: WebSocket) -> None:
        # Note: WebSocket acceptance is handled in the router to allow verification checks beforehand
        async with self._lock:
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        """Broadcast telemetry data payload directly to all connected websocket clients."""
        serialized_msg = json.dumps(message)
        disconnected = []

        async with self._lock:
            active_snapshot = list(self.active_connections)

        for connection in active_snapshot:
            try:
                await connection.send_text(serialized_msg)
            except Exception:
                disconnected.append(connection)

        # Cleanup inactive connections
        for conn in disconnected:
            await self.disconnect(conn)

    async def publish_telemetry(self, message: dict) -> None:
        """Publishes telemetry data. Routes through Redis if enabled, otherwise broadcasts locally."""
        if self.redis_client:
            try:
                await self.redis_client.publish("telemetry_channel", json.dumps(message))
            except Exception as exc:
                logger.error(f"Failed to publish to Redis Pub/Sub: {exc}. Falling back to local in-memory broadcast.")
                await self.broadcast(message)
        else:
            await self.broadcast(message)


# Singleton instance of the connection manager
manager = ConnectionManager()
