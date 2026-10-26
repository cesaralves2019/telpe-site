"""UK Contracts Finder, OCDS search API. Open, no key. Rate-limited: on a 403, stop for 5 minutes.

Docs: https://www.contractsfinder.service.gov.uk/apidocumentation/Notices/1/GET-Published-Notice-OCDS-Search
England, Wales and (most) Northern Ireland notices, including sub-threshold ones.
Scotland publishes on Public Contracts Scotland; above-threshold UK notices also go to Find a Tender.
"""
from __future__ import annotations

import time
from datetime import date, datetime, timezone

import httpx

from . import parse_iso

API_URL = "https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search"


def search(since: date, until: date | None = None, max_pages: int = 10) -> list[dict]:
    until = until or date.today()
    params = {"publishedFrom": f"{since:%Y-%m-%d}T00:00:00", "publishedTo": f"{until:%Y-%m-%d}T23:59:59",
              "stages": "tender", "limit": 100}
    releases, cursor = [], None
    for _ in range(max_pages):
        if cursor:
            params["cursor"] = cursor
        r = httpx.get(API_URL, params=params, timeout=60, headers={"Accept": "application/json"})
        if r.status_code == 403:
            raise RuntimeError("Contracts Finder rate limit hit; wait 5 minutes before the next call")
        r.raise_for_status()
        data = r.json()
        batch = data.get("releases") or []
        releases.extend(batch)
        cursor = data.get("nextCursor") or (data.get("links") or {}).get("next")
        if cursor and cursor.startswith("http"):  # some responses give a full next URL
            cursor = cursor.split("cursor=")[-1].split("&")[0]
        if not batch or not cursor:
            break
        time.sleep(1)
    return releases


def normalize(rel: dict) -> dict:
    tender = rel.get("tender") or {}
    buyer = (rel.get("buyer") or {}).get("name")
    if not buyer:
        for p in rel.get("parties") or []:
            if "buyer" in (p.get("roles") or []):
                buyer = p.get("name")
                break
    value = (tender.get("value") or {}).get("amount")
    currency = (tender.get("value") or {}).get("currency") or ("GBP" if value is not None else None)
    cpv = []
    regions = []
    for item in tender.get("items") or []:
        cls = item.get("classification") or {}
        if cls.get("id"):
            cpv.append(str(cls["id"]))
        for addr in item.get("deliveryAddresses") or []:
            if addr.get("region"):
                regions.append(str(addr["region"]))
    end = (tender.get("tenderPeriod") or {}).get("endDate")
    deadline_dt = parse_iso(end)
    deadline = datetime(deadline_dt.year, deadline_dt.month, deadline_dt.day, tzinfo=timezone.utc) if deadline_dt else None
    notice_id = rel.get("id") or rel.get("ocid")
    url = None
    for doc in tender.get("documents") or []:
        u = doc.get("url") or ""
        if "contractsfinder.service.gov.uk/notice" in u.lower():
            url = u
            break
    url = url or f"https://www.contractsfinder.service.gov.uk/Notice/{notice_id}"
    return {
        "_id": f"contracts_finder:{notice_id}", "source": "contracts_finder", "source_id": str(notice_id),
        "title": tender.get("title") or "", "description": tender.get("description"), "buyer": buyer or "",
        "cpv": list(dict.fromkeys(cpv)), "country": "GB", "nuts": list(dict.fromkeys(regions)), "place": None,
        "value": float(value) if value is not None else None, "currency": currency,
        "published_at": parse_iso(rel.get("date")), "deadline": deadline, "url": url,
        "raw": {"ocid": rel.get("ocid"), "id": rel.get("id"), "tags": rel.get("tag")},
    }


def fetch(since: date) -> list[dict]:
    return [normalize(r) for r in search(since) if (r.get("tender") or {}).get("title")]
