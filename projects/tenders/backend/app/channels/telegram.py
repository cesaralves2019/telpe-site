"""Telegram Bot API. Free, no templates, no 24-hour window.

Setup: talk to @BotFather → /newbot → copy the token into TELEGRAM_BOT_TOKEN.
Local development: `python -m app.poll_telegram` (long polling, no public URL needed).
Production:        `python -m app.channels.telegram set-webhook https://your-host/webhooks/telegram`
"""
from __future__ import annotations

import html
import json
import re
import sys

import httpx

from .. import config
from . import Inbound


def api(method: str, **payload) -> dict:
    if not config.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/{method}"
    r = httpx.post(url, json=payload, timeout=30)
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {data.get('description')} ({r.status_code})")
    return data["result"]


def to_html(text: str) -> str:
    """Our *bold* / _italic_ markup → Telegram HTML, with everything else escaped."""
    out = html.escape(text, quote=False)
    out = re.sub(r"\*(.+?)\*", r"<b>\1</b>", out)
    out = re.sub(r"(?<![\w/])_(.+?)_(?!\w)", r"<i>\1</i>", out)
    return out


CONTACT_KEYBOARD = {
    "keyboard": [[{"text": "Share my number", "request_contact": True}], [{"text": "SKIP"}]],
    "resize_keyboard": True,
    "one_time_keyboard": True,
}
REMOVE_KEYBOARD = {"remove_keyboard": True}


def send_text(chat_id: str | int, text: str, keyboard: dict | None = None) -> str:
    """Returns the Telegram message id."""
    payload = {"chat_id": chat_id, "text": to_html(text), "parse_mode": "HTML", "disable_web_page_preview": True}
    if keyboard:
        payload["reply_markup"] = keyboard
    result = api("sendMessage", **payload)
    return str(result.get("message_id"))


def parse_update(update: dict) -> Inbound | None:
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return None
    chat_id = str(msg["chat"]["id"])
    sender = msg.get("from") or {}
    name = " ".join(x for x in (sender.get("first_name"), sender.get("last_name")) if x) or sender.get("username")
    phone = None
    contact = msg.get("contact")
    if contact and str(contact.get("user_id")) == str(sender.get("id")):  # only their own number
        phone = re.sub(r"\D", "", contact.get("phone_number") or "") or None
    text = (msg.get("text") or msg.get("caption") or "").strip()
    return Inbound(channel="telegram", external_id=chat_id, text=text, name=name, phone=phone,
                   message_id=str(msg.get("message_id")), raw=update)


def set_webhook(url: str) -> dict:
    payload = {"url": url, "allowed_updates": ["message"], "drop_pending_updates": True}
    if config.TELEGRAM_WEBHOOK_SECRET:
        payload["secret_token"] = config.TELEGRAM_WEBHOOK_SECRET
    return api("setWebhook", **payload)


def delete_webhook() -> dict:
    return api("deleteWebhook", drop_pending_updates=False)


def get_updates(offset: int | None, timeout: int = 30) -> list[dict]:
    payload = {"timeout": timeout, "allowed_updates": ["message"]}
    if offset is not None:
        payload["offset"] = offset
    if not config.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getUpdates"
    r = httpx.post(url, json=payload, timeout=timeout + 10)
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram getUpdates failed: {data.get('description')}")
    return data["result"]


def bot_link() -> str | None:
    return f"https://t.me/{config.TELEGRAM_BOT_USERNAME}" if config.TELEGRAM_BOT_USERNAME else None


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "set-webhook" and len(sys.argv) > 2:
        print(json.dumps(set_webhook(sys.argv[2]), indent=2))
    elif cmd == "delete-webhook":
        print(json.dumps(delete_webhook(), indent=2))
    elif cmd == "me":
        print(json.dumps(api("getMe"), indent=2))
    else:
        print("usage: python -m app.channels.telegram set-webhook <https-url> | delete-webhook | me")
