"""Minimal governance WebSocket stream manager."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import WebSocket


class GovernanceStreamManager:
    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections[client_id] = websocket
        await websocket.send_json(
            {
                "type": "governance_snapshot",
                "timestamp": 0,
                "data": {"quotas": {}},
            }
        )

    def disconnect(self, client_id: str) -> None:
        self.active_connections.pop(client_id, None)

    async def broadcast_quota_update(self, capability_id: str, quota_state: Dict[str, Any]) -> None:
        payload = {
            "type": "quota_update",
            "data": {"capability_id": capability_id, **quota_state},
        }
        await self._broadcast(payload)

    async def broadcast_governance_event(self, event_type: str, data: Dict[str, Any]) -> None:
        payload = {"type": "governance_event", "event_type": event_type, "data": data}
        await self._broadcast(payload)

    async def _broadcast(self, payload: Dict[str, Any]) -> None:
        for websocket in list(self.active_connections.values()):
            try:
                await websocket.send_json(payload)
            except Exception:
                continue


manager = GovernanceStreamManager()


__all__ = ["GovernanceStreamManager", "manager"]
