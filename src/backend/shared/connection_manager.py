from fastapi import WebSocket
from typing import Dict, List
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # topic_id -> list of active WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, topic_id: str):
        await websocket.accept()
        if topic_id not in self.active_connections:
            self.active_connections[topic_id] = []
        self.active_connections[topic_id].append(websocket)
        logger.info(f"WebSocket client connected to topic {topic_id}. Total clients: {len(self.active_connections[topic_id])}")

    def disconnect(self, websocket: WebSocket, topic_id: str):
        if topic_id in self.active_connections:
            if websocket in self.active_connections[topic_id]:
                self.active_connections[topic_id].remove(websocket)
                logger.info(f"WebSocket client disconnected from topic {topic_id}. Remaining clients: {len(self.active_connections[topic_id])}")
            if not self.active_connections[topic_id]:
                del self.active_connections[topic_id]

    async def broadcast_topic_status(self, topic_id: str, status_data: dict):
        if topic_id in self.active_connections:
            message = json.dumps(status_data)
            # Create a copy of the list to avoid issues if a client disconnects during broadcast
            connections = list(self.active_connections[topic_id])
            for connection in connections:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to WebSocket client for topic {topic_id}: {e}")
                    self.disconnect(connection, topic_id)

manager = ConnectionManager()
