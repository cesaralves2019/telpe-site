"""A small timetable loop, so the whole thing runs as two processes (web + scheduler)
without a queue or cron. Checks every 30 seconds, in the TIMEZONE from config:

  fetch      every FETCH_EVERY_MINUTES
  daily      at DAILY_SEND_AT, every day
  weekly     at WEEKLY_SEND_AT on Mondays
  reminders  at REMINDERS_AT, every day

The `jobs` collection remembers the last run, so a restart never sends twice.
    python -m app.scheduler
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import config, db, jobs


def last_run(name: str) -> datetime | None:
    doc = db.jobs().find_one({"_id": name})
    return doc.get("ran_at") if doc else None


def due_daily(name: str, hhmm: str, now: datetime, weekday: int | None = None) -> bool:
    if weekday is not None and now.weekday() != weekday:
        return False
    h, m = (int(x) for x in hhmm.split(":"))
    if (now.hour, now.minute) < (h, m):
        return False
    last = last_run(name)
    return last is None or last.astimezone(now.tzinfo).date() < now.date()


def tick(now: datetime | None = None) -> list[str]:
    now = now or datetime.now(ZoneInfo(config.TIMEZONE))
    ran = []
    last = last_run("fetch")
    if last is None or now - last.astimezone(now.tzinfo) >= timedelta(minutes=config.FETCH_EVERY_MINUTES):
        print(now.isoformat(timespec="seconds"), "fetch", jobs.fetch())
        ran.append("fetch")
    if due_daily("daily", config.DAILY_SEND_AT, now):
        print(now.isoformat(timespec="seconds"), "daily", jobs.daily())
        ran.append("daily")
    if due_daily("weekly", config.WEEKLY_SEND_AT, now, weekday=0):
        print(now.isoformat(timespec="seconds"), "weekly", jobs.weekly())
        ran.append("weekly")
    if due_daily("reminders", config.REMINDERS_AT, now):
        print(now.isoformat(timespec="seconds"), "reminders", jobs.reminders())
        ran.append("reminders")
    return ran


if __name__ == "__main__":
    db.ensure_indexes()
    print("scheduler up; timezone", config.TIMEZONE)
    while True:
        try:
            tick()
        except Exception as e:  # keep going; the next tick retries
            print("tick failed:", e)
        time.sleep(30)
