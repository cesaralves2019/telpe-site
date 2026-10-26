"""Where tenders come from. Each module has fetch(since: date) -> list[dict].

A normalised tender looks like:
{
  "_id": "ted:123456-2026",         # "<source>:<source_id>", so re-fetching upserts
  "source": "ted" | "contracts_finder" | "etenders",
  "source_id": "123456-2026",
  "title": str, "description": str | None, "buyer": str,
  "cpv": ["77310000"], "country": "IE" | "GB", "nuts": ["IE061"], "place": str | None,
  "value": float | None, "currency": "EUR" | "GBP" | None,
  "published_at": datetime (UTC), "deadline": datetime | None (midnight UTC of the closing day),
  "url": str, "raw": dict (whatever the source gave us, for debugging),
}
matcher.enrich() then adds sectors, region, band and sub.
"""
from datetime import date, datetime, timezone


def utc(d: date | None) -> datetime | None:
    """Store deadlines as datetimes at midnight UTC: Mongo has no date type."""
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc) if d else None


def parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s[:10] if len(s) == 10 else s)
    except ValueError:
        try:
            dt = datetime.fromisoformat(s[:19])
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
