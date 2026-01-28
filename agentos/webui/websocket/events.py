"""
Events WebSocket - Real-time event streaming to WebUI

Sprint B Task #4: WebSocket event broadcast

WS /ws/events - Server-to-client event stream

Architecture:
- Client connects → registers as EventBus subscriber
- Core emits event → broadcasted to all connected clients
- Client disconnects → auto cleanup

Event Protocol (v1):
{
  "type": "task.progress",
  "ts": "2026-01-27T10:21:33.123Z",
  "source": "core",
  "entity": {
    "kind": "task",
    "id": "task_abc123"
  },
  "payload": {
    "progress": 42,
    "message": "Indexing documents"
  }
}
"""

import logging
import asyncio
import uuid
from typing import Dict, Set
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from agentos.core.events import Event, get_event_bus

logger = logging.getLogger(__name__)

router = APIRouter()


class EventStreamManager:
    """
    Manages WebSocket connections for event streaming

    Each connection registers as an EventBus subscriber.
    Events are broadcasted to all active connections.
    """

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self._event_bus = None
        self._subscriber_registered = False

    def _ensure_subscribed(self):
        """Ensure we're subscribed to EventBus (lazy initialization)"""
        if not self._subscriber_registered:
            self._event_bus = get_event_bus()
            self._event_bus.subscribe_async(self._on_event)
            self._subscriber_registered = True
            logger.info("EventStreamManager subscribed to EventBus")

    async def connect(self, client_id: str, websocket: WebSocket):
        """Accept and register WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Event stream client connected: {client_id} (total: {len(self.active_connections)})")

        # Ensure subscribed on first connection
        self._ensure_subscribed()

    def disconnect(self, client_id: str):
        """Remove WebSocket connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Event stream client disconnected: {client_id} (total: {len(self.active_connections)})")

    async def _on_event(self, event: Event):
        """
        EventBus callback: broadcast event to all connected clients

        This is called by EventBus whenever Core emits an event.
        """
        if not self.active_connections:
            # No clients connected, skip
            return

        # Serialize event once
        event_dict = event.to_dict()

        # Broadcast to all connected clients
        disconnected_clients = []

        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(event_dict)
            except Exception as e:
                logger.warning(f"Failed to send event to client {client_id}: {e}")
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

    async def broadcast_message(self, message: Dict):
        """Manually broadcast a message to all clients (for testing)"""
        for client_id, websocket in list(self.active_connections.items()):
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to broadcast to {client_id}: {e}")
                self.disconnect(client_id)


# Global manager instance
manager = EventStreamManager()


@router.websocket("/events")
async def websocket_events(websocket: WebSocket):
    """
    WebSocket event stream endpoint

    Client connection lifecycle:
    1. Connect → accept connection, register as subscriber
    2. Listen → receive events from Core via EventBus
    3. Disconnect → cleanup

    Server-to-client only (no client messages expected).

    Example client usage (JavaScript):
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/ws/events');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Event:', data.type, data.payload);
    };
    ```
    """
    # Generate unique client ID
    client_id = str(uuid.uuid4())

    await manager.connect(client_id, websocket)

    try:
        # Keep connection alive (server-to-client only)
        while True:
            # Wait for any message (used for keepalive/ping)
            # Client doesn't need to send messages, but we listen
            # to detect disconnection
            data = await websocket.receive_text()

            # Optional: handle ping/pong or client commands
            if data == "ping":
                await websocket.send_json({"type": "pong", "ts": datetime.now(timezone.utc).isoformat()})

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}", exc_info=True)
        manager.disconnect(client_id)


@router.get("/events/status")
async def get_event_stream_status():
    """
    Get event stream status (for monitoring)

    Returns number of active WebSocket connections.
    """
    return {
        "active_connections": len(manager.active_connections),
        "event_bus_subscribers": get_event_bus().subscriber_count(),
    }
