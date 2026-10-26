from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app import conversation, db, jobs, scheduler
from app.channels import Inbound
from app.sample_data import sample_tenders


def onboard(outbox, chat="42", mode_cmd=None):
    for t in ["/start", "2,6", "1", "5", "SKIP", "SKIP"]:
        conversation.handle(Inbound(channel="telegram", external_id=chat, text=t, name="Ana"))
    if mode_cmd:
        conversation.handle(Inbound(channel="telegram", external_id=chat, text=mode_cmd, name="Ana"))
    outbox.clear()


def test_upsert_is_idempotent():
    assert jobs.upsert_tenders(sample_tenders()) == 18
    assert jobs.upsert_tenders(sample_tenders()) == 0
    assert db.tenders().count_documents({}) == 18
    t = db.tenders().find_one({"_id": "sample:1"})
    assert t["sectors"] == ["landscaping"] and t["region"] == "dublin" and t["band"] == "m"


def test_daily_sends_once_per_tender(outbox):
    jobs.seed_sample()
    onboard(outbox)
    # the welcome already showed the best match; daily sends the next unseen one
    r = jobs.daily()
    assert r == {"sent": 1, "skipped": 0}
    assert "New tender ·" in outbox.last()["text"]
    n = db.alerts().count_documents({})
    jobs.daily()
    assert db.alerts().count_documents({}) == n + 1  # a different tender, never the same twice
    # once everything recent has been shown, nothing more is sent
    for _ in range(20):
        jobs.daily()
    total = db.alerts().count_documents({})
    assert jobs.daily() == {"sent": 0, "skipped": 0}
    assert db.alerts().count_documents({}) == total


def test_weekly_digest(outbox):
    jobs.seed_sample()
    onboard(outbox, mode_cmd="WEEKLY")
    assert jobs.weekly() == {"sent": 1}
    msg = outbox.last()["text"]
    assert "Your week in tenders" in msg and "Reply a number" in msg
    user = db.users().find_one({"telegram.chat_id": "42"})
    assert len(user["last_digest"]) == 3  # 4 fit the profile, the welcome message already showed one
    conversation.handle(Inbound(channel="telegram", external_id="42", text="2", name="Ana"))
    assert "New tender ·" in outbox.last()["text"]
    assert user["last_digest"][1] == db.users().find_one({"telegram.chat_id": "42"})["last_tender_id"]


def test_reminders(outbox):
    jobs.seed_sample()
    onboard(outbox)
    conversation.handle(Inbound(channel="telegram", external_id="42", text="SAVE", name="Ana"))
    user = db.users().find_one({"telegram.chat_id": "42"})
    today = conversation.today()
    d7 = today + timedelta(days=7)
    db.tenders().update_one({"_id": user["last_tender_id"]}, {"$set": {"deadline": datetime(d7.year, d7.month, d7.day, tzinfo=timezone.utc)}})
    outbox.clear()
    assert jobs.reminders() == {"sent": 1}
    assert "7 days left" in outbox.last()["text"]
    assert jobs.reminders() == {"sent": 0}  # not twice
    d2 = today + timedelta(days=2)
    db.tenders().update_one({"_id": user["last_tender_id"]}, {"$set": {"deadline": datetime(d2.year, d2.month, d2.day, tzinfo=timezone.utc)}})
    assert jobs.reminders() == {"sent": 1}
    assert "2 days left" in outbox.last()["text"]


def test_scheduler_runs_each_job_once_a_day(outbox, monkeypatch):
    clock = {}

    def fake_fetch(*a, **k):  # records the simulated time, like the real job records db.now()
        db.jobs().update_one({"_id": "fetch"}, {"$set": {"ran_at": clock["now"]}}, upsert=True)
        return {"ok": 1}

    def tick(now):
        clock["now"] = now
        monkeypatch.setattr(db, "now", lambda: now)
        return scheduler.tick(now)

    monkeypatch.setattr(jobs, "fetch", fake_fetch)
    tz = ZoneInfo("Europe/Dublin")
    monday_0810 = datetime(2026, 10, 12, 8, 10, tzinfo=tz)
    assert set(tick(monday_0810)) == {"fetch", "daily", "weekly"}
    assert tick(monday_0810 + timedelta(minutes=1)) == []
    assert tick(monday_0810 + timedelta(hours=1)) == ["fetch", "reminders"]
    tuesday = monday_0810 + timedelta(days=1)
    assert set(tick(tuesday)) == {"fetch", "daily"}


def test_stats():
    jobs.seed_sample()
    s = jobs.stats()
    assert s["tenders"] == 18 and s["open"] == 18
