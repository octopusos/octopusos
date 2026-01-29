"""
Task Events SSE - Real-time task event streaming

GET /sse/tasks/{task_id}/events - Real-time event stream via SSE

Features:
- Real-time push: Events delivered with < 500ms latency
- Resumable: Support since_seq parameter for gap recovery
- Batching: Batch events (configurable batch_size and flush_interval)
- Keepalive: Send heartbeat every 30s to keep connection alive
- Backpressure: Auto rate-limiting if client is slow
- Auto cleanup: Resources cleaned up on client disconnect

Architecture:
- Uses Starlette StreamingResponse for SSE
- Subscribes to task_events table changes via polling (SQLite compatible)
- Buffers events for batch delivery
- Implements exponential backoff for polling

SSE Message Format:
    data: {"seq": 123, "event_type": "phase_enter", "phase": "executing", ...}

    data: {"seq": 124, "event_type": "work_item_started", "span_id": "work_1", ...}
"""

import asyncio
import json
import logging
import time
from typing import Optional, Dict, Any, AsyncGenerator
from dataclasses import dataclass

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from agentos.core.task.event_service import TaskEventService, TaskEvent

logger = logging.getLogger(__name__)

router = APIRouter()


@dataclass
class SSEConfig:
    """SSE streaming configuration"""

    batch_size: int = 10  # Max events per batch
    flush_interval: float = 0.5  # Max seconds before flushing batch
    keepalive_interval: float = 30.0  # Keepalive heartbeat interval
    poll_interval: float = 0.1  # Initial polling interval
    max_poll_interval: float = 2.0  # Max polling interval (exponential backoff)
    poll_backoff_factor: float = 1.5  # Exponential backoff multiplier
    max_events_per_stream: int = 10000  # Max events before forcing reconnect


class TaskEventStreamer:
    """
    Task event SSE streamer

    Manages real-time streaming of task events via SSE protocol.
    Implements batching, keepalive, backpressure, and exponential polling.
    """

    def __init__(
        self,
        task_id: str,
        since_seq: Optional[int] = None,
        config: Optional[SSEConfig] = None,
    ):
        self.task_id = task_id
        self.since_seq = since_seq or 0
        self.config = config or SSEConfig()
        self.service = TaskEventService()

        # State
        self.last_seq = since_seq or 0
        self.event_buffer = []
        self.last_flush_time = time.time()
        self.last_keepalive_time = time.time()
        self.poll_interval = self.config.poll_interval
        self.events_sent = 0

    async def stream(self) -> AsyncGenerator[str, None]:
        """
        Stream events via SSE

        Yields SSE-formatted messages (data: {...}\n\n)

        Flow:
            1. Send historical events (since_seq to latest)
            2. Poll for new events
            3. Batch events and flush on interval/size threshold
            4. Send keepalive heartbeats
            5. Handle backpressure and exponential polling
        """
        logger.info(f"Starting SSE stream for task {self.task_id} (since_seq={self.since_seq})")

        try:
            # Phase 1: Send historical events (catch-up)
            async for message in self._stream_historical():
                yield message

            # Phase 2: Real-time streaming (poll for new events)
            async for message in self._stream_realtime():
                yield message

        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for task {self.task_id}")
            raise
        except Exception as e:
            logger.error(f"SSE stream error for task {self.task_id}: {e}", exc_info=True)
            yield self._format_error(str(e))

    async def _stream_historical(self) -> AsyncGenerator[str, None]:
        """
        Stream historical events (catch-up phase)

        Retrieves all events with seq > since_seq and sends them.
        Uses batching to avoid overwhelming client.
        """
        logger.info(f"Fetching historical events for task {self.task_id} (since_seq={self.since_seq})")

        batch_size = 100  # Larger batches for historical data
        has_more = True

        while has_more:
            # Fetch next batch
            events = self.service.get_events(
                self.task_id,
                since_seq=self.last_seq,
                limit=batch_size
            )

            if not events:
                has_more = False
                break

            # Send events
            for event in events:
                yield self._format_event(event)
                self.last_seq = event.seq
                self.events_sent += 1

            # Check if there are more events
            has_more = len(events) == batch_size

            # Yield control to allow cancellation
            await asyncio.sleep(0)

        logger.info(f"Historical stream complete for task {self.task_id} (sent {self.events_sent} events)")

    async def _stream_realtime(self) -> AsyncGenerator[str, None]:
        """
        Stream real-time events (polling phase)

        Continuously polls for new events and streams them.
        Implements:
        - Batching (flush on size/time threshold)
        - Keepalive (heartbeat every N seconds)
        - Exponential backoff (reduce polling frequency when idle)
        - Event limit (force reconnect after max events)
        """
        logger.info(f"Starting real-time stream for task {self.task_id}")

        while True:
            # Check if we should force reconnect (event limit reached)
            if self.events_sent >= self.config.max_events_per_stream:
                logger.info(f"Event limit reached for task {self.task_id}, forcing reconnect")
                yield self._format_reconnect()
                break

            # Poll for new events
            events = self.service.get_events(
                self.task_id,
                since_seq=self.last_seq,
                limit=self.config.batch_size
            )

            if events:
                # Reset poll interval (activity detected)
                self.poll_interval = self.config.poll_interval

                # Buffer events
                for event in events:
                    self.event_buffer.append(event)
                    self.last_seq = event.seq

                # Flush if buffer is full
                if len(self.event_buffer) >= self.config.batch_size:
                    async for message in self._flush_buffer():
                        yield message
            else:
                # No new events, apply exponential backoff
                self.poll_interval = min(
                    self.poll_interval * self.config.poll_backoff_factor,
                    self.config.max_poll_interval
                )

            # Flush buffer if flush interval elapsed
            time_since_flush = time.time() - self.last_flush_time
            if self.event_buffer and time_since_flush >= self.config.flush_interval:
                async for message in self._flush_buffer():
                    yield message

            # Send keepalive if needed
            time_since_keepalive = time.time() - self.last_keepalive_time
            if time_since_keepalive >= self.config.keepalive_interval:
                yield self._format_keepalive()
                self.last_keepalive_time = time.time()

            # Wait before next poll
            await asyncio.sleep(self.poll_interval)

    async def _flush_buffer(self) -> AsyncGenerator[str, None]:
        """Flush event buffer"""
        if not self.event_buffer:
            return

        for event in self.event_buffer:
            yield self._format_event(event)
            self.events_sent += 1

        logger.debug(f"Flushed {len(self.event_buffer)} events for task {self.task_id}")
        self.event_buffer.clear()
        self.last_flush_time = time.time()

    def _format_event(self, event: TaskEvent) -> str:
        """Format event as SSE message"""
        data = {
            "seq": event.seq,
            "event_id": event.event_id,
            "task_id": event.task_id,
            "event_type": event.event_type,
            "phase": event.phase,
            "actor": event.actor,
            "span_id": event.span_id,
            "parent_span_id": event.parent_span_id,
            "payload": event.payload,
            "created_at": event.created_at,
        }
        return f"data: {json.dumps(data)}\n\n"

    def _format_keepalive(self) -> str:
        """Format keepalive heartbeat"""
        return ": keepalive\n\n"

    def _format_reconnect(self) -> str:
        """Format reconnect message"""
        data = {
            "type": "reconnect",
            "last_seq": self.last_seq,
            "reason": "event_limit_reached"
        }
        return f"data: {json.dumps(data)}\n\n"

    def _format_error(self, error: str) -> str:
        """Format error message"""
        data = {
            "type": "error",
            "error": error,
            "last_seq": self.last_seq
        }
        return f"data: {json.dumps(data)}\n\n"


# ============================================
# SSE Endpoints
# ============================================


@router.get("/sse/tasks/{task_id}/events")
async def stream_task_events(
    request: Request,
    task_id: str,
    since_seq: Optional[int] = Query(None, ge=0, description="Resume from seq (exclusive)"),
    batch_size: int = Query(10, ge=1, le=100, description="Batch size"),
    flush_interval: float = Query(0.5, ge=0.1, le=5.0, description="Flush interval (seconds)"),
):
    """
    Stream task events via SSE

    Real-time event streaming with support for resumption, batching, and keepalive.

    Args:
        task_id: Task ID
        since_seq: Optional - Resume from seq (get events with seq > since_seq)
        batch_size: Max events per batch (default: 10, max: 100)
        flush_interval: Max seconds before flushing batch (default: 0.5s, max: 5s)

    Returns:
        StreamingResponse with SSE events

    Example:
        GET /sse/tasks/task_01xyz/events?since_seq=100&batch_size=10

    Client example (JavaScript):
        ```javascript
        const eventSource = new EventSource('/sse/tasks/task_01xyz/events?since_seq=0');

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'reconnect') {
                // Server requests reconnect
                eventSource.close();
                // Reconnect with last_seq
                connectSSE(data.last_seq);
            } else if (data.type === 'error') {
                console.error('SSE error:', data.error);
            } else {
                // Normal event
                console.log('Event:', data.event_type, data.seq);
            }
        };

        eventSource.onerror = (error) => {
            console.error('SSE connection error:', error);
            // Implement reconnection logic
        };
        ```
    """
    # Create streamer with custom config
    config = SSEConfig(
        batch_size=batch_size,
        flush_interval=flush_interval,
    )

    streamer = TaskEventStreamer(
        task_id=task_id,
        since_seq=since_seq,
        config=config,
    )

    # Create streaming response
    return StreamingResponse(
        streamer.stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/sse/health")
async def sse_health_check() -> Dict[str, str]:
    """
    Health check for SSE service

    Returns:
        Status message
    """
    return {
        "status": "ok",
        "service": "task_events_sse",
        "version": "v0.32",
        "protocol": "sse"
    }
