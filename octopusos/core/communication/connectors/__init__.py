"""Connectors for external communication services.

This module provides connector implementations for various
external services including web search, web fetch, RSS, email, and messaging.
"""

from octopusos.core.communication.connectors.base import BaseConnector
from octopusos.core.communication.connectors.web_search import WebSearchConnector
from octopusos.core.communication.connectors.web_fetch import WebFetchConnector
from octopusos.core.communication.connectors.rss import RSSConnector
from octopusos.core.communication.connectors.email_smtp import EmailSMTPConnector
from octopusos.core.communication.connectors.slack import SlackConnector

__all__ = [
    "BaseConnector",
    "WebSearchConnector",
    "WebFetchConnector",
    "RSSConnector",
    "EmailSMTPConnector",
    "SlackConnector",
]
