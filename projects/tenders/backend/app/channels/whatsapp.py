"""WhatsApp via Meta's Cloud API (no Twilio in between).

Rules that shape this file:
- A person must write to us first (or opt in). After their last message we have a
  24-hour "customer service window" in which free-form text is allowed (and free).
- Outside that window the only thing we may send is an approved *template*, charged
  per message (utility rate; Ireland is in "Rest of Western Europe"). So the daily
  alert, the Monday digest and reminders go out as templates; replies go as text.
- Template parameters cannot contain newlines, tabs or 4+ spaces (text.one_line()).

Setup is in the README ("WhatsApp"). You need WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID,
WHATSAPP_VERIFY_TOKEN (any string you choose) and, for signature checks, WHATSAPP_APP_SECRET.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import sys

import httpx

from .. import config
from . import Inbound


def _url(path: str) -> str:
    return f"https://graph.facebook.com/{config.GRAPH_API_VERSION}/{path}"


def _post(payload: dict) -> dict:
    if not (config.WHATSAPP_TOKEN and config.WHATSAPP_PHONE_NUMBER_ID):
        raise RuntimeError("WHATSAPP_TOKEN / WHATSAPP_PHONE_NUMBER_ID are not set")
    r = httpx.post(_url(f"{config.WHATSAPP_PHONE_NUMBER_ID}/messages"),
                   headers={"Authorization": f"Bearer {config.WHATSAPP_TOKEN}"}, json=payload, timeout=30)
    data = r.json()
    if r.status_code >= 400:
        err = data.get("error", {})
        raise RuntimeError(f"WhatsApp send failed ({r.status_code}): {err.get('message')} "
                           f"[code {err.get('code')}, subcode {err.get('error_subcode')}]")
    return data


def send_text(wa_id: str, text: str) -> str:
    """Free-form text. Only works inside the 24h window. Returns the message id (wamid...)."""
    data = _post({"messaging_product": "whatsapp", "recipient_type": "individual", "to": wa_id,
                  "type": "text", "text": {"preview_url": False, "body": text}})
    return data["messages"][0]["id"]


def send_template(wa_id: str, name: str, params: list[str], lang: str | None = None) -> str:
    """Approved template with body parameters {{1}}..{{n}}. Works any time."""
    components = []
    if params:
        components.append({"type": "body", "parameters": [{"type": "text", "text": p} for p in params]})
    data = _post({"messaging_product": "whatsapp", "to": wa_id, "type": "template",
                  "template": {"name": name, "language": {"code": lang or config.WHATSAPP_TEMPLATE_LANG},
                               "components": components}})
    return data["messages"][0]["id"]


def mark_read(message_id: str) -> None:
    try:
        _post({"messaging_product": "whatsapp", "status": "read", "message_id": message_id})
    except Exception:
        pass  # cosmetic


def verify_signature(raw_body: bytes, header: str | None) -> bool:
    """X-Hub-Signature-256: sha256=<hmac of the raw body with the app secret>."""
    if not config.WHATSAPP_APP_SECRET:
        return True  # not configured: accept, but set it before going live
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(config.WHATSAPP_APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header[7:])


def parse_webhook(payload: dict) -> list[Inbound]:
    """Messages only; delivery/read statuses are ignored here (logged by main.py if you want)."""
    out: list[Inbound] = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            names = {c.get("wa_id"): (c.get("profile") or {}).get("name") for c in value.get("contacts") or []}
            for m in value.get("messages") or []:
                kind = m.get("type")
                if kind == "text":
                    text = (m.get("text") or {}).get("body", "")
                elif kind == "button":
                    text = (m.get("button") or {}).get("text", "")
                elif kind == "interactive":
                    i = m.get("interactive") or {}
                    text = (i.get("button_reply") or i.get("list_reply") or {}).get("title", "")
                else:
                    text = ""  # image, audio, location...: we acknowledge but don't parse
                wa_id = str(m.get("from"))
                out.append(Inbound(channel="whatsapp", external_id=wa_id, text=text.strip(), name=names.get(wa_id),
                                   phone=re.sub(r"\D", "", wa_id), message_id=m.get("id"), raw=m))
    return out


def wa_me_link(prefill: str = "JOIN") -> str | None:
    return f"https://wa.me/{config.WHATSAPP_DISPLAY_NUMBER}?text={prefill}" if config.WHATSAPP_DISPLAY_NUMBER else None


if __name__ == "__main__":
    # Smoke test from the terminal: python -m app.channels.whatsapp hello 353851234567
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "hello" and len(sys.argv) > 2:
        print(send_template(sys.argv[2], "hello_world", [], "en_US"))
    elif cmd == "text" and len(sys.argv) > 3:
        print(send_text(sys.argv[2], " ".join(sys.argv[3:])))
    else:
        print("usage: python -m app.channels.whatsapp hello <wa_id> | text <wa_id> <message>")
        print(json.dumps({"phone_number_id": config.WHATSAPP_PHONE_NUMBER_ID, "token_set": bool(config.WHATSAPP_TOKEN)}))
