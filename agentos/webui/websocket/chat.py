"""
Chat WebSocket - Real-time chat interface

WS /ws/chat/{session_id} - WebSocket chat endpoint

Refactored in v0.3.2 (P1 Sprint W-P1-02):
- Integrated with agentos.core.chat.engine.ChatEngine (replaces Echo)
- Added streaming support
- Persistent message storage via SessionStore
- Error handling with structured responses
- Runtime config pipeline (Phase 3)
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# Import ChatEngine
from agentos.core.chat.engine import ChatEngine

# Import SessionStore (injected via app.py)
from agentos.webui.api.sessions import get_session_store

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Runtime Config (Phase 3)
# ============================================================================

@dataclass
class ChatRuntimeConfig:
    """
    Runtime configuration for ChatEngine

    Extracted from WebSocket message.metadata and passed to Core session.
    Supports model selection, provider selection, and generation parameters.
    """
    model_type: Optional[str] = None  # "local" | "cloud"
    provider: Optional[str] = None    # "ollama" | "openai" | "anthropic" | etc.
    model: Optional[str] = None       # Model name (e.g., "qwen2.5:32b", "gpt-4")
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None

    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate config values

        Returns:
            (is_valid, error_message)
        """
        # Validate model_type
        if self.model_type is not None and self.model_type not in ("local", "cloud"):
            return False, f"Invalid model_type: {self.model_type} (must be 'local' or 'cloud')"

        # Validate temperature
        if self.temperature is not None:
            if not isinstance(self.temperature, (int, float)):
                return False, f"Invalid temperature type: {type(self.temperature).__name__} (must be number)"
            if not (0.0 <= self.temperature <= 2.0):
                return False, f"Invalid temperature: {self.temperature} (must be 0.0-2.0)"

        # Validate top_p
        if self.top_p is not None:
            if not isinstance(self.top_p, (int, float)):
                return False, f"Invalid top_p type: {type(self.top_p).__name__} (must be number)"
            if not (0.0 <= self.top_p <= 1.0):
                return False, f"Invalid top_p: {self.top_p} (must be 0.0-1.0)"

        # Validate max_tokens
        if self.max_tokens is not None:
            if not isinstance(self.max_tokens, int):
                return False, f"Invalid max_tokens type: {type(self.max_tokens).__name__} (must be int)"
            if self.max_tokens <= 0:
                return False, f"Invalid max_tokens: {self.max_tokens} (must be > 0)"

        return True, None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict, excluding None values"""
        return {k: v for k, v in asdict(self).items() if v is not None}


def extract_runtime_config(metadata: Dict[str, Any]) -> tuple[ChatRuntimeConfig, Optional[str]]:
    """
    Extract and normalize runtime config from WebSocket metadata

    Whitelist approach: Only extract known fields, ignore unknown fields.

    Args:
        metadata: Raw metadata from WebSocket message

    Returns:
        (config, error_message)
        If extraction fails, returns (empty_config, error_message)
    """
    try:
        config = ChatRuntimeConfig(
            model_type=metadata.get("model_type") or metadata.get("modelType"),
            provider=metadata.get("provider"),
            model=metadata.get("model"),
            temperature=metadata.get("temperature"),
            top_p=metadata.get("top_p") or metadata.get("topP"),
            max_tokens=metadata.get("max_tokens") or metadata.get("maxTokens"),
        )

        # Validate extracted config
        is_valid, error = config.validate()
        if not is_valid:
            return ChatRuntimeConfig(), error

        return config, None

    except Exception as e:
        logger.error(f"Failed to extract runtime config: {e}", exc_info=True)
        return ChatRuntimeConfig(), f"Config extraction error: {str(e)}"


class ConnectionManager:
    """Manage WebSocket connections"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """Accept and register connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected: session={session_id}")

    def disconnect(self, session_id: str):
        """Remove connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected: session={session_id}")

    async def send_message(self, session_id: str, message: Dict[str, Any]):
        """Send message to specific session"""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_json(message)

    async def send_text(self, session_id: str, text: str):
        """Send text message to specific session"""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_text(text)


manager = ConnectionManager()

# Global ChatEngine instance (initialized on first use)
_chat_engine: Optional[ChatEngine] = None


def get_chat_engine() -> ChatEngine:
    """Get or create ChatEngine instance (singleton)"""
    global _chat_engine
    if _chat_engine is None:
        _chat_engine = ChatEngine()
        logger.info("ChatEngine initialized")
    return _chat_engine


@router.websocket("/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket chat endpoint

    Handles bidirectional communication:
    - Receives user messages
    - Sends assistant responses (streaming)
    - Sends tool calls
    - Sends events

    Message format (client -> server):
    {
        "type": "user_message",
        "content": "...",
        "metadata": {
            "model_type": "local",     # Optional: "local" | "cloud"
            "provider": "ollama",      # Optional: "ollama" | "openai" | "anthropic"
            "model": "qwen2.5:32b",    # Optional: Model name
            "temperature": 0.7,        # Optional: 0.0-2.0
            "top_p": 0.9,              # Optional: 0.0-1.0
            "max_tokens": 2048         # Optional: Max output tokens
        }
    }

    Message format (server -> client):
    {
        "type": "message.start" | "message.delta" | "message.end" | "message.error" | "event",
        "content": "...",
        "message_id": "...",           # Unique message ID
        "metadata": {}
    }
    """
    await manager.connect(session_id, websocket)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get("type", "user_message")
                content = message.get("content", "")
                metadata = message.get("metadata", {})

                logger.info(f"Received message: session={session_id}, type={message_type}, len={len(content)}")

                # Handle user message
                if message_type == "user_message":
                    await handle_user_message(session_id, content, metadata)

                else:
                    # Unknown message type
                    await manager.send_message(session_id, {
                        "type": "error",
                        "content": f"Unknown message type: {message_type}",
                    })

            except json.JSONDecodeError:
                await manager.send_message(session_id, {
                    "type": "error",
                    "content": "Invalid JSON",
                })
            except Exception as e:
                logger.error(f"Error handling message: {e}", exc_info=True)
                await manager.send_message(session_id, {
                    "type": "error",
                    "content": f"Internal error: {str(e)}",
                })

    except WebSocketDisconnect:
        manager.disconnect(session_id)


async def handle_user_message(session_id: str, content: str, metadata: Dict[str, Any]):
    """
    Handle user message and generate response

    Phase 1 Implementation:
    - Stores user message to WebUI SessionStore
    - Calls ChatEngine for response generation
    - Streams response back to client
    - Stores assistant message to WebUI SessionStore

    Phase 3 Implementation:
    - Extracts runtime config from metadata
    - Passes config to Core session
    - Structured error handling for invalid config

    Architecture Decision:
    - ChatEngine writes to chat_sessions/chat_messages (Core audit)
    - WebUI writes to webui_sessions/webui_messages (UI display)
    - No coupling between storage layers
    """
    store = get_session_store()

    # Phase 3: Extract runtime config from metadata
    logger.info(f"📩 Received metadata from WebUI: {metadata}")
    runtime_config, config_error = extract_runtime_config(metadata)

    if config_error:
        logger.error(f"Invalid runtime config: {config_error}")
        await manager.send_message(session_id, {
            "type": "message.error",
            "content": f"⚠️ Configuration error: {config_error}",
            "metadata": {
                "error_type": "invalid_config",
                "error_detail": config_error,
            },
        })
        return

    # Log extracted config
    config_dict = runtime_config.to_dict()
    if config_dict:
        logger.info(f"Runtime config: {config_dict}")

    try:
        # 1. Store user message to WebUI
        user_msg = store.add_message(
            session_id=session_id,
            role="user",
            content=content,
            metadata=metadata
        )
        logger.info(f"Stored user message: {user_msg.message_id}")

    except ValueError as e:
        # Session not found or validation error
        logger.error(f"Failed to store user message: {e}")
        await manager.send_message(session_id, {
            "type": "error",
            "content": f"Failed to save message: {str(e)}",
        })
        return

    # 2. Get ChatEngine
    try:
        chat_engine = get_chat_engine()
    except Exception as e:
        logger.error(f"Failed to initialize ChatEngine: {e}", exc_info=True)
        await manager.send_message(session_id, {
            "type": "error",
            "content": "Chat engine unavailable. Please check configuration.",
        })
        return

    # 3. Ensure Core chat session exists with runtime config
    # Note: ChatEngine expects its own session_id in chat_sessions table
    # We create it on-demand if needed, passing runtime_config as session metadata
    try:
        from agentos.core.chat.service import ChatService
        chat_service = ChatService()

        # Try to get session, create if not exists
        try:
            existing_session = chat_service.get_session(session_id)

            # If session exists but config changed, update metadata
            if config_dict:
                logger.info(f"Updating Core session with runtime config: {config_dict}")
                try:
                    chat_service.update_session_metadata(session_id, config_dict)
                    logger.info(f"✓ Updated session metadata: {config_dict}")
                except Exception as e:
                    logger.error(f"Failed to update session metadata: {e}")

        except Exception:
            # Session doesn't exist, create it with runtime config
            session_metadata = {
                "title": f"WebUI Session {session_id[:8]}",
                "source": "webui",
                **config_dict,  # Merge runtime config into session metadata
            }

            chat_service.create_session(
                title=session_metadata["title"],
                metadata=session_metadata,
                session_id=session_id  # Use WebUI's session_id
            )
            logger.info(f"Created Core chat session: {session_id} with config: {config_dict}")

    except Exception as e:
        logger.warning(f"Failed to ensure Core chat session: {e}")
        # Not fatal, continue (ChatEngine will use defaults)

    # 4. Call ChatEngine with streaming (Phase 2: Real streaming)
    response_buffer = []
    message_id = str(uuid.uuid4())

    try:
        # Send message.start event
        await manager.send_message(session_id, {
            "type": "message.start",
            "message_id": message_id,
            "role": "assistant",
            "metadata": {},
        })

        # Get streaming generator from ChatEngine
        stream_generator = chat_engine.send_message(
            session_id=session_id,
            user_input=content,
            stream=True  # Phase 2: real streaming
        )

        # Iterate over chunks and stream to client in real-time
        # Note: ChatEngine._stream_response() is a synchronous generator
        # We use asyncio.Queue to bridge sync generator and async WebSocket

        chunk_queue = asyncio.Queue()

        async def producer():
            """Run sync generator in thread, feed chunks to queue"""
            loop = asyncio.get_event_loop()

            def sync_iterate():
                try:
                    for chunk in stream_generator:
                        # Put chunk in queue (thread-safe)
                        asyncio.run_coroutine_threadsafe(
                            chunk_queue.put(("chunk", chunk)),
                            loop
                        )
                except Exception as e:
                    asyncio.run_coroutine_threadsafe(
                        chunk_queue.put(("error", str(e))),
                        loop
                    )
                finally:
                    # Signal completion
                    asyncio.run_coroutine_threadsafe(
                        chunk_queue.put(("done", None)),
                        loop
                    )

            # Run in thread pool
            await loop.run_in_executor(None, sync_iterate)

        # Start producer task
        producer_task = asyncio.create_task(producer())

        # Consume chunks from queue and send to client
        try:
            while True:
                msg_type, data = await chunk_queue.get()

                if msg_type == "chunk":
                    response_buffer.append(data)

                    await manager.send_message(session_id, {
                        "type": "message.delta",
                        "content": data,
                        "metadata": {},
                    })

                elif msg_type == "error":
                    raise Exception(data)

                elif msg_type == "done":
                    break

        except asyncio.CancelledError:
            # WebSocket disconnected, cancel producer
            producer_task.cancel()
            logger.warning(f"Streaming cancelled for session {session_id}")
            raise

        # Send message.end event
        full_response = "".join(response_buffer)

        await manager.send_message(session_id, {
            "type": "message.end",
            "message_id": message_id,
            "content": full_response,
            "metadata": {
                "total_chunks": len(response_buffer),
                "total_chars": len(full_response)
            },
        })

        logger.info(f"Streamed response: {len(response_buffer)} chunks, {len(full_response)} chars")

    except Exception as e:
        logger.error(f"ChatEngine streaming error: {e}", exc_info=True)

        error_message = f"⚠️ Chat engine error: {str(e)}"
        response_buffer = [error_message]

        await manager.send_message(session_id, {
            "type": "message.error",
            "message_id": message_id,
            "content": error_message,
            "metadata": {},
        })

    # 5. Store assistant message to WebUI (only once, at the end)
    try:
        full_response = "".join(response_buffer)

        # Only store if we have content (not just error)
        if full_response and not full_response.startswith("⚠️"):
            assistant_msg = store.add_message(
                session_id=session_id,
                role="assistant",
                content=full_response,
                metadata={
                    "streamed": True,
                    "total_chunks": len(response_buffer),
                    "total_chars": len(full_response),
                    "webui_message_id": message_id
                }
            )

            logger.info(f"Stored assistant message: {assistant_msg.message_id} (WebUI msg: {message_id})")

        else:
            logger.warning(f"Skipped storing error message: {full_response[:100]}")

    except Exception as e:
        logger.error(f"Failed to store assistant message: {e}", exc_info=True)
        # Not fatal, message was already sent to user
        # Send error notification to client
        await manager.send_message(session_id, {
            "type": "event",
            "content": "storage_error",
            "metadata": {"error": str(e)},
        })
