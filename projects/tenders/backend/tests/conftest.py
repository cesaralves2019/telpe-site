import os

os.environ["MONGODB_URI"] = "mongomock://"
os.environ["MONGODB_DB"] = "telpe_test"
os.environ["TELEGRAM_BOT_TOKEN"] = "123:test"
os.environ["TELEGRAM_WEBHOOK_SECRET"] = "s3cret"
os.environ["WHATSAPP_TOKEN"] = "wa-test"
os.environ["WHATSAPP_PHONE_NUMBER_ID"] = "111"
os.environ["WHATSAPP_APP_SECRET"] = "app-secret"
os.environ["WHATSAPP_VERIFY_TOKEN"] = "verify-me"
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest  # noqa: E402

from app import db  # noqa: E402
from app.channels import telegram, whatsapp  # noqa: E402


class Outbox:
    """Captures what would have gone to Telegram / WhatsApp."""

    def __init__(self):
        self.items = []

    def telegram(self, chat_id, text, keyboard=None):
        self.items.append({"channel": "telegram", "to": str(chat_id), "text": text, "keyboard": keyboard})
        return f"tg-{len(self.items)}"

    def wa_text(self, wa_id, text):
        self.items.append({"channel": "whatsapp", "to": wa_id, "text": text, "template": None})
        return f"wamid-{len(self.items)}"

    def wa_template(self, wa_id, name, params, lang=None):
        self.items.append({"channel": "whatsapp", "to": wa_id, "text": None, "template": name, "params": params})
        return f"wamid-{len(self.items)}"

    def texts(self):
        return [i["text"] for i in self.items if i.get("text")]

    def last(self):
        return self.items[-1]

    def clear(self):
        self.items.clear()


@pytest.fixture
def outbox(monkeypatch):
    box = Outbox()
    monkeypatch.setattr(telegram, "send_text", box.telegram)
    monkeypatch.setattr(whatsapp, "send_text", box.wa_text)
    monkeypatch.setattr(whatsapp, "send_template", box.wa_template)
    monkeypatch.setattr(whatsapp, "mark_read", lambda mid: None)
    return box


@pytest.fixture(autouse=True)
def clean_db():
    db.reset_for_tests()
    db.ensure_indexes()
    yield
    db.reset_for_tests()
