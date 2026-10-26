"""Messaging channels. Each adapter knows how to send a text and how to turn its
webhook payload into an Inbound. Everything else (who the user is, what to reply)
lives in conversation.py and goes out through router.deliver()."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Inbound:
    channel: str                # "telegram" | "whatsapp"
    external_id: str            # telegram chat_id or whatsapp wa_id, as a string
    text: str = ""              # what the person typed (or pressed), may be empty for a contact share
    name: str | None = None     # display name if the channel gives one
    phone: str | None = None    # E.164-ish digits when known (WhatsApp always; Telegram only if shared)
    message_id: str | None = None
    raw: dict = field(default_factory=dict)
