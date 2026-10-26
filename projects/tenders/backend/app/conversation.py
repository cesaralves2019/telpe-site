"""What happens when a person writes to us, on either channel.

One state machine for onboarding (sectors → region → size → keywords → [phone on
Telegram]) and a handful of commands afterwards (MORE, SAVE, SAVED, PROFILE, EDIT,
DAILY, WEEKLY, STOP, START, HELP). Replies go out through router.deliver(), so the
same code serves Telegram and WhatsApp.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from . import config, db, matcher, text
from .channels import Inbound, router, telegram

COMMANDS = {"MORE", "SAVE", "SAVED", "PROFILE", "EDIT", "DAILY", "WEEKLY", "STOP", "START", "HELP", "JOIN", "/START", "/HELP", "/STOP"}


def today() -> date:
    return datetime.now(ZoneInfo(config.TIMEZONE)).date()


def new_profile() -> dict:
    return {"sectors": [], "region": "all", "band": "any", "keywords": [], "sub": True}


# --- users --------------------------------------------------------------------

def find_or_create(inb: Inbound) -> dict:
    users = db.users()
    now = db.now()
    user = None
    if inb.channel == "telegram":
        user = users.find_one({"telegram.chat_id": inb.external_id})
        if user is None and inb.phone:
            user = users.find_one({"phone": inb.phone})
            if user is not None:
                users.update_one({"_id": user["_id"]}, {"$set": {"telegram": {"chat_id": inb.external_id, "linked_at": now}}})
    else:
        user = users.find_one({"whatsapp.wa_id": inb.external_id})
        if user is None and inb.phone:
            user = users.find_one({"phone": inb.phone})
            if user is not None:
                users.update_one({"_id": user["_id"]}, {"$set": {"whatsapp": {"wa_id": inb.external_id, "opted_in_at": now, "last_inbound_at": now}}})
    if user is None:
        doc = {"phone": inb.phone, "name": inb.name, "profile": new_profile(), "state": None, "status": "onboarding",
               "mode": "daily", "min_fit": config.MIN_FIT, "last_tender_id": None, "last_digest": [],
               "created_at": now, "updated_at": now}
        if inb.channel == "telegram":
            doc["telegram"] = {"chat_id": inb.external_id, "linked_at": now}
        else:
            doc["whatsapp"] = {"wa_id": inb.external_id, "opted_in_at": now, "last_inbound_at": now}
        if doc["phone"] is None:
            del doc["phone"]  # sparse unique index: don't store null
        doc["_id"] = users.insert_one(doc).inserted_id
        return doc
    sets = {"updated_at": now}
    if inb.channel == "whatsapp":
        sets["whatsapp.last_inbound_at"] = now
    if not user.get("name") and inb.name:
        sets["name"] = inb.name
    users.update_one({"_id": user["_id"]}, {"$set": sets})
    return users.find_one({"_id": user["_id"]})


def set_fields(user: dict, **fields) -> dict:
    fields["updated_at"] = db.now()
    db.users().update_one({"_id": user["_id"]}, {"$set": fields})
    user.update(fields)
    return user


def link_phone(user: dict, phone: str) -> dict:
    """Telegram user shared their number: attach it, merging with a WhatsApp account if one exists."""
    users = db.users()
    other = users.find_one({"phone": phone, "_id": {"$ne": user["_id"]}})
    if other is not None:
        merged = {"phone": phone}
        if other.get("whatsapp"):
            merged["whatsapp"] = other["whatsapp"]
        if other.get("status") == "active" and user.get("status") != "active":
            merged.update({"profile": other["profile"], "status": "active", "state": "active", "mode": other.get("mode", "daily")})
        users.delete_one({"_id": other["_id"]})
        db.alerts().update_many({"user_id": other["_id"]}, {"$set": {"user_id": user["_id"]}})
        return set_fields(user, **merged)
    return set_fields(user, phone=phone)


# --- tenders ------------------------------------------------------------------

def open_tenders() -> list[dict]:
    """Everything still open (or with no deadline), newest first."""
    t = today()
    return list(db.tenders().find({"$or": [{"deadline": {"$gte": datetime(t.year, t.month, t.day)}}, {"deadline": None}]})
                .sort("published_at", -1).limit(2000))


def unseen(user: dict, candidates: list[dict]) -> list[dict]:
    seen = {a["tender_id"] for a in db.alerts().find({"user_id": user["_id"]}, {"tender_id": 1})}
    return [t for t in candidates if t["_id"] not in seen]


def as_dates(t: dict) -> dict:
    """Mongo stores dates as datetimes; the matcher and text want a date for the deadline."""
    d = t.get("deadline")
    if isinstance(d, datetime):
        t = dict(t, deadline=d.date())
    return t


def record_alert(user: dict, t: dict, fit: int, kind: str) -> None:
    db.alerts().update_one({"user_id": user["_id"], "tender_id": t["_id"]},
                           {"$setOnInsert": {"user_id": user["_id"], "tender_id": t["_id"], "fit": fit, "kind": kind,
                                             "sent_at": db.now(), "saved": False, "reminders_sent": []}}, upsert=True)


def show_tender(user: dict, t: dict, fit: int, more: int = 0, kind: str = "alert") -> dict | None:
    t = as_dates(t)
    sector = matcher.best_sector(t, user["profile"])
    entry = router.deliver(user, text.alert(t, fit, sector, today(), more),
                           template=(config.WHATSAPP_TEMPLATE_ALERT, text.alert_params(t, fit, sector, today())), kind=kind)
    if entry and entry["status"] == "sent":
        record_alert(user, t, fit, kind)
        set_fields(user, last_tender_id=t["_id"])
    return entry


def send_next_match(user: dict, intro: bool = False) -> bool:
    ranked = matcher.rank([as_dates(t) for t in unseen(user, open_tenders())], user["profile"], today(), user.get("min_fit"))
    if intro:
        router.deliver(user, text.first_matches_intro(len(ranked)))
    if not ranked:
        if not intro:
            router.deliver(user, text.no_more())
        return False
    fit, t = ranked[0]
    show_tender(user, t, fit, more=len(ranked) - 1, kind="more" if not intro else "welcome")
    return True


# --- parsing ------------------------------------------------------------------

def numbers(s: str, upto: int) -> list[int]:
    found = [int(n) for n in re.findall(r"\d+", s)]
    return [n for n in dict.fromkeys(found) if 1 <= n <= upto]


# --- the flow -----------------------------------------------------------------

def handle(inb: Inbound) -> None:
    user = find_or_create(inb)
    db.messages().insert_one({"direction": "in", "channel": inb.channel, "user_id": user["_id"], "text": inb.text,
                              "at": db.now(), "provider_id": inb.message_id})
    cmd = inb.text.strip().upper()

    # Telegram contact share (no text, just a phone)
    if inb.channel == "telegram" and inb.phone and not inb.text:
        user = link_phone(user, inb.phone)
        router.deliver(user, text.telegram_linked("+" + inb.phone), keyboard=telegram.REMOVE_KEYBOARD)
        if user.get("state") == "ask_phone":
            finish(user)
        return

    state = user.get("state")

    # Commands that work at any time
    if cmd in ("STOP", "/STOP"):
        set_fields(user, status="paused")
        router.deliver(user, text.stopped())
        return
    if cmd == "HELP" or cmd == "/HELP":
        router.deliver(user, text.help_text())
        return
    if cmd == "DELETE":  # GDPR: everything about this person goes, after the goodbye is sent
        router.deliver(user, text.deleted())
        db.alerts().delete_many({"user_id": user["_id"]})
        db.messages().delete_many({"user_id": user["_id"]})
        db.users().delete_one({"_id": user["_id"]})
        return
    if cmd == "EDIT":
        set_fields(user, profile=new_profile(), state="ask_sectors", status="onboarding")
        router.deliver(user, text.ask_sectors())
        return

    # Onboarding
    if state is None or (state != "active" and cmd in ("/START", "JOIN", "START", "HI", "HELLO")):
        set_fields(user, state="ask_sectors", status="onboarding")
        router.deliver(user, text.welcome(user.get("name")))
        router.deliver(user, text.ask_sectors())
        return
    if state == "ask_sectors":
        picked = numbers(cmd, len(matcher.SECTOR_KEYS))
        if not picked:
            router.deliver(user, text.invalid_choice())
            return
        user["profile"]["sectors"] = [matcher.SECTOR_KEYS[n - 1] for n in picked]
        set_fields(user, profile=user["profile"], state="ask_region")
        router.deliver(user, text.ask_region())
        return
    if state == "ask_region":
        picked = numbers(cmd, len(matcher.REGION_KEYS))
        if not picked:
            router.deliver(user, text.invalid_choice())
            return
        user["profile"]["region"] = matcher.REGION_KEYS[picked[0] - 1]
        set_fields(user, profile=user["profile"], state="ask_size")
        router.deliver(user, text.ask_size())
        return
    if state == "ask_size":
        picked = numbers(cmd, len(matcher.VALUE_KEYS))
        if not picked:
            router.deliver(user, text.invalid_choice())
            return
        user["profile"]["band"] = matcher.VALUE_KEYS[picked[0] - 1]
        set_fields(user, profile=user["profile"], state="ask_keywords")
        router.deliver(user, text.ask_keywords())
        return
    if state == "ask_keywords":
        user["profile"]["keywords"] = [] if cmd in ("SKIP", "NO", "NONE", "-") else matcher.keywords_from(inb.text)
        set_fields(user, profile=user["profile"])
        if inb.channel == "telegram" and not user.get("phone") and not user.get("asked_phone"):
            set_fields(user, state="ask_phone", asked_phone=True)
            router.deliver(user, text.ask_phone_telegram(), keyboard=telegram.CONTACT_KEYBOARD)
            return
        finish(user)
        return
    if state == "ask_phone":  # SKIP, or anything else: carry on without a phone number
        router.deliver(user, "No problem.", keyboard=telegram.REMOVE_KEYBOARD)
        finish(user)
        return

    # Active (or paused) user
    if cmd in ("START", "/START"):
        set_fields(user, status="active")
        router.deliver(user, text.resumed())
        return
    if user.get("status") == "paused":
        set_fields(user, status="active")  # any message after STOP resumes, like WhatsApp etiquette expects
    if cmd == "MORE":
        send_next_match(user)
        return
    if cmd == "SAVE":
        tid = user.get("last_tender_id")
        t = db.tenders().find_one({"_id": tid}) if tid else None
        if not t:
            router.deliver(user, text.nothing_to_save())
            return
        db.alerts().update_one({"user_id": user["_id"], "tender_id": tid}, {"$set": {"saved": True, "saved_at": db.now()}})
        router.deliver(user, text.saved(as_dates(t)))
        return
    if cmd == "SAVED":
        ids = [a["tender_id"] for a in db.alerts().find({"user_id": user["_id"], "saved": True})]
        items = [as_dates(t) for t in db.tenders().find({"_id": {"$in": ids}}).sort("deadline", 1)]
        router.deliver(user, text.saved_list(items, today()))
        return
    if cmd == "PROFILE":
        router.deliver(user, text.profile_text(user["profile"]))
        return
    if cmd in ("DAILY", "WEEKLY"):
        set_fields(user, mode=cmd.lower())
        router.deliver(user, text.mode_set(cmd.lower()))
        return
    if cmd.isdigit() and user.get("last_digest"):
        n = int(cmd)
        if 1 <= n <= len(user["last_digest"]):
            tid = user["last_digest"][n - 1]
            t = db.tenders().find_one({"_id": tid})
            alert = db.alerts().find_one({"user_id": user["_id"], "tender_id": tid})
            if t:
                fit = (alert or {}).get("fit") or matcher.fit(as_dates(t), user["profile"], today()) or 0
                show_tender(user, t, fit, kind="digest-item")
                return
    router.deliver(user, text.not_understood())


def finish(user: dict) -> None:
    set_fields(user, state="active", status="active")
    router.deliver(user, text.done(user["profile"], user.get("mode", "daily")))
    send_next_match(user, intro=True)
