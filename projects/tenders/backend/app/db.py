"""MongoDB access. One client, a handful of collections, indexes created once.

Collections (all documents are plain dicts; see README "Data model"):
  users     one per person. Keyed by phone when we know it; also by telegram.chat_id / whatsapp.wa_id
  tenders   one per notice, _id = "<source>:<source_id>" so re-fetching never duplicates
  alerts    one per (user, tender) we have shown; carries fit, saved flag and reminder state
  messages  log of every inbound and outbound message, for debugging and audits
  jobs      last-run timestamps so the scheduler never double-sends after a restart
"""
from datetime import datetime, timezone

from pymongo import ASCENDING, DESCENDING, MongoClient

from . import config

_client = None


def client():
    global _client
    if _client is None:
        # tz_aware: datetimes come back with tzinfo=UTC, so they compare safely with db.now()
        if config.MONGODB_URI.startswith("mongomock://"):
            import mongomock  # test-only dependency
            _client = mongomock.MongoClient(tz_aware=True)
        else:
            _client = MongoClient(config.MONGODB_URI, tz_aware=True, serverSelectionTimeoutMS=8000)
    return _client


def db():
    return client()[config.MONGODB_DB]


def users():
    return db()["users"]


def tenders():
    return db()["tenders"]


def alerts():
    return db()["alerts"]


def messages():
    return db()["messages"]


def jobs():
    return db()["jobs"]


def ensure_indexes():
    users().create_index("phone", unique=True, sparse=True)
    users().create_index("telegram.chat_id", unique=True, sparse=True)
    users().create_index("whatsapp.wa_id", unique=True, sparse=True)
    users().create_index("status")
    tenders().create_index([("published_at", DESCENDING)])
    tenders().create_index("deadline")
    tenders().create_index("source")
    alerts().create_index([("user_id", ASCENDING), ("tender_id", ASCENDING)], unique=True)
    alerts().create_index([("user_id", ASCENDING), ("sent_at", DESCENDING)])
    alerts().create_index("saved")
    messages().create_index([("user_id", ASCENDING), ("at", DESCENDING)])


def now() -> datetime:
    return datetime.now(timezone.utc)


def reset_for_tests():
    """Drop everything. Only meaningful with mongomock."""
    global _client
    if _client is not None:
        _client.drop_database(config.MONGODB_DB)
