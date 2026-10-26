import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from app import db
from app.channels import telegram
from app.main import app
from app.text import alert


def test_whatsapp_verify_handshake():
    with TestClient(app) as c:
        r = c.get("/webhooks/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "12345"})
        assert r.status_code == 200 and r.text == "12345"
        r = c.get("/webhooks/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "1"})
        assert r.status_code == 403


def test_whatsapp_inbound_runs_conversation(outbox):
    payload = {"object": "whatsapp_business_account", "entry": [{"id": "1", "changes": [{"field": "messages", "value": {
        "messaging_product": "whatsapp", "metadata": {"display_phone_number": "15550000000", "phone_number_id": "111"},
        "contacts": [{"profile": {"name": "Ana"}, "wa_id": "353851234567"}],
        "messages": [{"from": "353851234567", "id": "wamid.1", "timestamp": "1760000000", "type": "text", "text": {"body": "JOIN"}}]}}]}]}
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(b"app-secret", body, hashlib.sha256).hexdigest()
    with TestClient(app) as c:
        assert c.post("/webhooks/whatsapp", content=body, headers={"X-Hub-Signature-256": "sha256=bad", "Content-Type": "application/json"}).status_code == 403
        r = c.post("/webhooks/whatsapp", content=body, headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"})
        assert r.status_code == 200
    assert db.users().count_documents({"whatsapp.wa_id": "353851234567"}) == 1
    assert "What do you sell" in outbox.texts()[-1]


def test_telegram_inbound_checks_secret(outbox):
    update = {"update_id": 1, "message": {"message_id": 5, "chat": {"id": 42}, "from": {"id": 42, "first_name": "Ana"}, "text": "/start"}}
    with TestClient(app) as c:
        assert c.post("/webhooks/telegram", json=update).status_code == 403
        assert c.post("/webhooks/telegram", json=update, headers={"X-Telegram-Bot-Api-Secret-Token": "s3cret"}).status_code == 200
    assert db.users().count_documents({"telegram.chat_id": "42"}) == 1
    assert outbox.last()["channel"] == "telegram"


def test_telegram_html_conversion():
    assert telegram.to_html("*New tender* <b> & _soon_") == "<b>New tender</b> &lt;b&gt; &amp; <i>soon</i>"
    assert "<b>New tender · OPW</b>" in telegram.to_html(alert(
        {"buyer": "OPW", "title": "Stonework", "value": 640000, "currency": "EUR", "deadline": None, "url": "https://x", "sub": False},
        88, "Construction & civil works"))
