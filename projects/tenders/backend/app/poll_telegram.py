"""Local development without a public URL: ask Telegram for updates in a loop.
Telegram refuses polling while a webhook is set, so this deletes the webhook first.

    python -m app.poll_telegram
"""
from __future__ import annotations

import time

from . import conversation, db
from .channels import telegram

if __name__ == "__main__":
    db.ensure_indexes()
    telegram.delete_webhook()
    me = telegram.api("getMe")
    print(f"polling as @{me.get('username')} — open https://t.me/{me.get('username')} and send /start")
    offset = None
    while True:
        try:
            for update in telegram.get_updates(offset):
                offset = update["update_id"] + 1
                inb = telegram.parse_update(update)
                if inb:
                    print("<-", inb.external_id, inb.text or f"[contact {inb.phone}]")
                    try:
                        conversation.handle(inb)
                    except Exception as e:
                        print("handle failed:", e)
        except Exception as e:
            print("poll failed:", e)
            time.sleep(5)
