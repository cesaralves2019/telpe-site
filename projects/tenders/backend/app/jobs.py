"""The scheduled work: fetch notices, send daily alerts, Monday digests, deadline reminders.

    python -m app.jobs fetch        # pull new notices from TED, Contracts Finder and eTenders
    python -m app.jobs daily        # one alert to every active daily user who has a fit
    python -m app.jobs weekly       # Monday digest to weekly users
    python -m app.jobs reminders    # 7-day and 2-day reminders for saved tenders
    python -m app.jobs all          # the four above, in order
    python -m app.jobs seed-sample  # load the 18 illustrative notices to try the bot without fetching
    python -m app.jobs stats        # counts

scheduler.py calls these on a timetable; you can also run them from cron.
"""
from __future__ import annotations

import sys
import traceback
from datetime import date, datetime, timedelta, timezone

from . import config, conversation, db, matcher, text
from .channels import router
from .sources import contracts_finder, etenders, ted
from .summarize import summarize

SOURCES = {"ted": ted.fetch, "contracts_finder": contracts_finder.fetch, "etenders": etenders.fetch}


def upsert_tenders(items: list[dict]) -> int:
    """Insert new notices, refresh changed fields on known ones. Returns how many were new."""
    new = 0
    col = db.tenders()
    for t in items:
        t = matcher.enrich(dict(t))
        existing = col.find_one({"_id": t["_id"]}, {"_id": 1, "summary": 1})
        if existing is None:
            t["first_seen"] = db.now()
            t["summary"] = summarize(t)
            col.insert_one(t)
            new += 1
        else:
            t.pop("summary", None)
            col.update_one({"_id": t["_id"]}, {"$set": {**t, "last_seen": db.now()}})
    return new


def fetch(days: int = 2, only: str | None = None) -> dict:
    since = date.today() - timedelta(days=days)
    report = {}
    for name, fn in SOURCES.items():
        if only and name != only:
            continue
        try:
            items = fn(since)
            report[name] = {"fetched": len(items), "new": upsert_tenders(items)}
        except Exception as e:
            report[name] = {"error": str(e)[:300]}
            traceback.print_exc()
    db.jobs().update_one({"_id": "fetch"}, {"$set": {"ran_at": db.now(), "report": report}}, upsert=True)
    return report


def active_users(mode: str | None = None):
    q = {"status": "active", "state": "active"}
    if mode:
        q["mode"] = mode
    return list(db.users().find(q))


def recent_tenders(hours: int) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    return [conversation.as_dates(t) for t in db.tenders().find({"published_at": {"$gte": since}}).sort("published_at", -1)]


def daily(hours: int = 36) -> dict:
    """One alert per user (DAILY_LIMIT), from notices published in the last `hours`, never repeated."""
    sent = skipped = 0
    candidates = recent_tenders(hours)
    for user in active_users("daily"):
        ranked = matcher.rank(conversation.unseen(user, candidates), user["profile"], conversation.today(), user.get("min_fit"))
        for i, (fit, t) in enumerate(ranked[: config.DAILY_LIMIT]):
            entry = conversation.show_tender(user, t, fit, more=len(ranked) - 1 - i, kind="alert")
            if entry and entry["status"] == "sent":
                sent += 1
            else:
                skipped += 1
    db.jobs().update_one({"_id": "daily"}, {"$set": {"ran_at": db.now(), "sent": sent, "skipped": skipped}}, upsert=True)
    return {"sent": sent, "skipped": skipped}


def weekly() -> dict:
    sent = 0
    candidates = recent_tenders(7 * 24)
    for user in active_users("weekly"):
        ranked = matcher.rank(conversation.unseen(user, candidates), user["profile"], conversation.today(), user.get("min_fit"))[: config.DIGEST_SIZE]
        entry = router.deliver(user, text.digest(ranked, conversation.today()),
                               template=(config.WHATSAPP_TEMPLATE_DIGEST, text.digest_params(ranked, config.DIGEST_SIZE)), kind="digest")
        if entry and entry["status"] == "sent":
            sent += 1
            for fit, t in ranked:
                conversation.record_alert(user, t, fit, "digest")
            conversation.set_fields(user, last_digest=[t["_id"] for _, t in ranked], last_tender_id=ranked[0][1]["_id"] if ranked else None)
    db.jobs().update_one({"_id": "weekly"}, {"$set": {"ran_at": db.now(), "sent": sent}}, upsert=True)
    return {"sent": sent}


def reminders(at_days: tuple[int, ...] = (7, 2)) -> dict:
    sent = 0
    today = conversation.today()
    for a in db.alerts().find({"saved": True}):
        t = db.tenders().find_one({"_id": a["tender_id"]})
        if not t or not t.get("deadline"):
            continue
        t = conversation.as_dates(t)
        left = (t["deadline"] - today).days
        if left in at_days and left not in (a.get("reminders_sent") or []):
            user = db.users().find_one({"_id": a["user_id"], "status": "active"})
            if not user:
                continue
            entry = router.deliver(user, text.reminder(t, left),
                                   template=(config.WHATSAPP_TEMPLATE_REMINDER, text.reminder_params(t, left)), kind="reminder")
            if entry and entry["status"] == "sent":
                db.alerts().update_one({"_id": a["_id"]}, {"$push": {"reminders_sent": left}})
                sent += 1
    db.jobs().update_one({"_id": "reminders"}, {"$set": {"ran_at": db.now(), "sent": sent}}, upsert=True)
    return {"sent": sent}


def seed_sample() -> int:
    from .sample_data import sample_tenders
    return upsert_tenders(sample_tenders())


def stats() -> dict:
    return {
        "users": db.users().count_documents({}),
        "active": db.users().count_documents({"status": "active"}),
        "tenders": db.tenders().count_documents({}),
        "open": len(conversation.open_tenders()),
        "alerts": db.alerts().count_documents({}),
        "saved": db.alerts().count_documents({"saved": True}),
        "messages_out_failed": db.messages().count_documents({"direction": "out", "status": "failed"}),
        "jobs": {j["_id"]: j.get("ran_at") for j in db.jobs().find()},
    }


if __name__ == "__main__":
    db.ensure_indexes()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "fetch":
        print(fetch(only=sys.argv[2] if len(sys.argv) > 2 else None))
    elif cmd == "daily":
        print(daily())
    elif cmd == "weekly":
        print(weekly())
    elif cmd == "reminders":
        print(reminders())
    elif cmd == "all":
        print({"fetch": fetch(), "daily": daily(), "weekly": weekly() if date.today().weekday() == 0 else "not Monday", "reminders": reminders()})
    elif cmd == "seed-sample":
        print({"new": seed_sample()})
    elif cmd == "stats":
        print(stats())
    else:
        print(__doc__)
