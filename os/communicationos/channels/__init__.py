"""Channel adapters for CommunicationOS.

This package contains specific channel adapter implementations that integrate
external communication platforms with OctopusOS.

Available Adapters:
    - whatsapp_twilio: WhatsApp integration via Twilio's Business API
    - telegram: Telegram Bot API integration
    - slack: Slack integration via Slack Events API
    - imessage: iMessage integration via bridge webhook
    - bridge_im: generic bridge adapter for additional IM channels
"""

from octopusos.communicationos.channels.whatsapp_twilio import (
    WhatsAppTwilioAdapter,
    verify_twilio_signature,
)
from octopusos.communicationos.channels.telegram import (
    TelegramAdapter,
    send_message as telegram_send_message,
    set_webhook as telegram_set_webhook,
)
from octopusos.communicationos.channels.slack import (
    SlackAdapter,
    post_message as slack_post_message,
    verify_signature as slack_verify_signature,
    auth_test as slack_auth_test,
)
from octopusos.communicationos.channels.imessage import IMessageAdapter
from octopusos.communicationos.channels.bridge_im import GenericBridgeIMAdapter

__all__ = [
    "WhatsAppTwilioAdapter",
    "verify_twilio_signature",
    "TelegramAdapter",
    "telegram_send_message",
    "telegram_set_webhook",
    "SlackAdapter",
    "slack_post_message",
    "slack_verify_signature",
    "slack_auth_test",
    "IMessageAdapter",
    "GenericBridgeIMAdapter",
]
