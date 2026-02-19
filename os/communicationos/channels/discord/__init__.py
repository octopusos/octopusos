"""Discord Channel Adapter.

This module provides the Discord channel adapter for CommunicationOS.
"""

# Import client for direct usage
from octopusos.communicationos.channels.discord.client import (
    DiscordClient,
    DiscordClientError,
    DiscordRateLimitError,
    DiscordAuthError,
    DiscordInteractionExpiredError,
)

# Import adapter
from octopusos.communicationos.channels.discord.adapter import DiscordAdapter

__all__ = [
    "DiscordClient",
    "DiscordClientError",
    "DiscordRateLimitError",
    "DiscordAuthError",
    "DiscordInteractionExpiredError",
    "DiscordAdapter",
]
