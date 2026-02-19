"""Feishu/Lark enterprise IM adapter for CommunicationOS.

This is a bridge-only adapter:
- Receives official event callbacks (via WebUI API webhook endpoint)
- Verifies token/signature and decrypts (if enabled)
- Maps inbound events to InboundMessage and pushes into MessageBus
- Sends outbound text via Feishu OpenAPI

No prompt logic, tool calls, or policy decisions live here. Those belong to core runtime.
"""

from .adapter import FeishuAdapter

__all__ = ["FeishuAdapter"]

