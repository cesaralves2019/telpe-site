"""TED (Tenders Electronic Daily) Search API v3. Open, no key, fair use ~700 requests/min.

Docs: https://docs.ted.europa.eu/api/latest/  ·  Swagger: https://api.ted.europa.eu/swagger-ui/index.html
Query syntax is TED's "expert search" (same as on ted.europa.eu). Irish notices reach
TED 1–3 days after eTenders, so this source is for cross-checking and for UK/EU
above-threshold notices; eTenders is the one that is early.
"""
from __future__ import annotations

import time
from datetime import date

import httpx

from . import parse_iso, utc

API_URL = "https://api.ted.europa.eu/v3/notices/search"
PAGE_SIZE = 100
# Competition notices only (not awards, not planning). Codes from the eForms notice-type list.
NOTICE_TYPES = "cn-standard cn-social cn-desg subco qu-sy"
FIELDS = ["publication-number", "publication-date", "notice-type", "notice-title", "title-proc", "buyer-name",
          "buyer-country", "buyer-city", "classification-cpv", "deadline-receipt-tender-date-lot",
          "estimated-value-proc", "estimated-value-cur-proc", "links"]
OPTIONAL_FIELDS = ["description-proc", "place-of-performance"]  # dropped automatically if the API rejects them
COUNTRY = {"IRL": "IE", "GBR": "GB"}


def _first(v):
    return (v[0] if v else None) if isinstance(v, list) else v


def pick_lang(value, lang3: str = "eng") -> str:
    if isinstance(value, dict):
        for k in (lang3, "eng", "mul", *value.keys()):
            v = _first(value.get(k))
            if v:
                return str(v).strip()
        return ""
    v = _first(value)
    return "" if v is None else str(v).strip()


def query_for(since: date, countries: str = "IRL GBR") -> str:
    return (f"publication-date>={since:%Y%m%d} AND buyer-country IN ({countries}) "
            f"AND notice-type IN ({NOTICE_TYPES}) SORT BY publication-date DESC")


def search(query: str, max_pages: int = 10, fields: list[str] | None = None) -> list[dict]:
    fields = fields or FIELDS + OPTIONAL_FIELDS
    notices, total = [], 0
    for page in range(1, max_pages + 1):
        body = {"query": query, "fields": fields, "page": page, "limit": PAGE_SIZE,
                "paginationMode": "PAGE_NUMBER", "scope": "ALL"}
        r = httpx.post(API_URL, json=body, timeout=60)
        if r.status_code == 400 and any(f in fields for f in OPTIONAL_FIELDS):
            return search(query, max_pages, [f for f in fields if f not in OPTIONAL_FIELDS])
        r.raise_for_status()
        res = r.json()
        batch = res.get("notices") or []
        total = int(res.get("totalNoticeCount") or 0)
        notices.extend(batch)
        if len(batch) < PAGE_SIZE or len(notices) >= total:
            break
        time.sleep(0.5)
    return notices


def normalize(n: dict) -> dict:
    pub = str(n.get("publication-number") or "")
    deadlines = sorted({str(d)[:10] for d in (n.get("deadline-receipt-tender-date-lot") or []) if d})
    deadline = date.fromisoformat(deadlines[-1]) if deadlines else None
    try:
        value = float(_first(n.get("estimated-value-proc")))
    except (TypeError, ValueError):
        value = None
    links = (n.get("links") or {}).get("html") or {}
    url = links.get("ENG") or links.get("eng") or f"https://ted.europa.eu/en/notice/-/detail/{pub}"
    country3 = _first(n.get("buyer-country")) or ""
    places = n.get("place-of-performance") or []
    return {
        "_id": f"ted:{pub}", "source": "ted", "source_id": pub,
        "title": pick_lang(n.get("title-proc")) or pick_lang(n.get("notice-title")),
        "description": pick_lang(n.get("description-proc")) or None,
        "buyer": pick_lang(n.get("buyer-name")),
        "cpv": list(dict.fromkeys(str(c) for c in (n.get("classification-cpv") or []))),
        "country": COUNTRY.get(country3, country3[:2]),
        "nuts": [str(p) for p in places] if isinstance(places, list) else [],
        "place": pick_lang(n.get("buyer-city")) or None,
        "value": value,
        "currency": str(_first(n.get("estimated-value-cur-proc")) or ("EUR" if value else "")) or None,
        "published_at": parse_iso(str(_first(n.get("publication-date")) or "")),
        "deadline": utc(deadline),
        "url": url,
        "raw": {k: n.get(k) for k in ("publication-number", "notice-type", "buyer-country", "classification-cpv")},
    }


def fetch(since: date) -> list[dict]:
    return [normalize(n) for n in search(query_for(since))]
