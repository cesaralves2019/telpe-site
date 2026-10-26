"""Decides where a message goes and sends it.

The rule Cesar set: if the person has Telegram, use Telegram; otherwise WhatsApp.
(Telegram is also free and has no template rules, so it's the cheaper path.)

deliver(user, text, template=(name, params)) handles the WhatsApp 24-hour window:
inside it → free text; outside it → the template, if one was given; otherwise it
logs a skip and returns None.
"""
from __future__ import annotations

from datetime import timedelta

from .. import db
from . import telegram, whatsapp

WINDOW = timedelta(hours=24)


def preferred_channel(user: dict) -> str | None:
    if (user.get("telegram") or {}).get("chat_id"):
        return "telegram"
    if (user.get("whatsapp") or {}).get("wa_id"):
        return "whatsapp"
    return None


def window_open(user: dict) -> bool:
    last = (user.get("whatsapp") or {}).get("last_inbound_at")
    return bool(last) and db.now() - last < WINDOW


def deliver(user: dict, text: str, template: tuple[str, list[str]] | None = None,
            keyboard: dict | None = None, kind: str = "reply") -> dict | None:
    """Send `text` on the user's preferred channel. Returns the message log entry, or None if skipped."""
    channel = preferred_channel(user)
    entry = {"direction": "out", "channel": channel, "user_id": user["_id"], "kind": kind, "text": text,
             "at": db.now(), "status": "sent", "provider_id": None, "error": None}
    try:
        if channel == "telegram":
            entry["provider_id"] = telegram.send_text(user["telegram"]["chat_id"], text, keyboard=keyboard)
        elif channel == "whatsapp":
            wa_id = user["whatsapp"]["wa_id"]
            if window_open(user):
                entry["provider_id"] = whatsapp.send_text(wa_id, text)
            elif template:
                name, params = template
                entry["template"] = name
                entry["provider_id"] = whatsapp.send_template(wa_id, name, params)
            else:
                entry["status"] = "skipped"
                entry["error"] = "WhatsApp window closed and no template for this message"
        else:
            entry["status"] = "skipped"
            entry["error"] = "user has no channel"
    except Exception as e:  # network, auth, template not approved...
        entry["status"] = "failed"
        entry["error"] = str(e)[:500]
    db.messages().insert_one(entry)
    return entry
