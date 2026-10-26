"""HTTP side: the two webhooks, a health check and the join links for the website.

    uvicorn app.main:app --host 0.0.0.0 --port 8000

Meta and Telegram both need a public HTTPS URL. Locally: `ngrok http 8000` (or
`cloudflared tunnel --url http://localhost:8000`) and use the URL it prints.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse

from . import config, conversation, db
from .channels import telegram, whatsapp


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.ensure_indexes()
    yield


app = FastAPI(title="Telpe Tenders", lifespan=lifespan)


@app.get("/health")
def health():
    return {"ok": True, "telegram": bool(config.TELEGRAM_BOT_TOKEN), "whatsapp": bool(config.WHATSAPP_TOKEN),
            "db": config.MONGODB_DB}


@app.get("/links")
def links():
    """For the website's 'Start free' button: one link per channel."""
    return {"telegram": telegram.bot_link(), "whatsapp": whatsapp.wa_me_link("JOIN")}


# --- WhatsApp -----------------------------------------------------------------

@app.get("/webhooks/whatsapp")
def whatsapp_verify(request: Request):
    """Meta calls this once when you save the webhook URL in the app dashboard."""
    q = request.query_params
    if q.get("hub.mode") == "subscribe" and q.get("hub.verify_token") == config.WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(q.get("hub.challenge", ""))
    raise HTTPException(status_code=403, detail="verify token mismatch")


@app.post("/webhooks/whatsapp")
async def whatsapp_inbound(request: Request, background: BackgroundTasks,
                           x_hub_signature_256: str | None = Header(default=None)):
    raw = await request.body()
    if not whatsapp.verify_signature(raw, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="bad signature")
    payload = await request.json()
    for inb in whatsapp.parse_webhook(payload):
        background.add_task(conversation.handle, inb)  # answer Meta fast, work after
        if inb.message_id:
            background.add_task(whatsapp.mark_read, inb.message_id)
    return {"ok": True}


# --- Telegram -----------------------------------------------------------------

@app.post("/webhooks/telegram")
async def telegram_inbound(request: Request, background: BackgroundTasks,
                           x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    if config.TELEGRAM_WEBHOOK_SECRET and x_telegram_bot_api_secret_token != config.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="bad secret")
    update = await request.json()
    inb = telegram.parse_update(update)
    if inb:
        background.add_task(conversation.handle, inb)
    return {"ok": True}
