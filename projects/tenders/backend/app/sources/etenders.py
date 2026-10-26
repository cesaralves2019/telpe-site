"""eTenders (Ireland). No API and no RSS, but the "Latest CfTs" list is public:
https://www.etenders.gov.ie/epps/prepareCurrentOpportunities.do?currentType=cft

We read that HTML table (title, contracting authority, date published, submission
deadline, status, estimated value, link) a few pages at a time, newest first, and
stop at the first row older than `since`. One request per second, a handful of pages
a day: lighter than a person clicking through. Check the site's terms of use before
running this at scale, and expect the markup to change now and then; test_sources.py
has a fixture to keep the parser honest.

For history (who won what since 2013) use the OGP open dataset instead:
https://data.gov.ie/dataset/contract-notices-published-on-etenders (CSV, CC BY 4.0).
"""
from __future__ import annotations

import re
import time
from datetime import date, datetime, timezone

import httpx
from bs4 import BeautifulSoup

BASE = "https://www.etenders.gov.ie"
LIST_URL = BASE + "/epps/prepareCurrentOpportunities.do"
HEADERS = {"User-Agent": "TelpeTenders/0.1 (+https://telpe.ai)", "Accept-Language": "en-IE,en;q=0.8"}
# "Mon Oct 12 11:03:44 IST 2026" → we drop the zone token; Python's %Z won't parse IST
DATE_RE = re.compile(r"^(\w{3} \w{3} \d{1,2} \d{2}:\d{2}:\d{2}) [A-Z]{2,5} (\d{4})$")


def parse_date(s: str | None) -> datetime | None:
    s = " ".join((s or "").split())
    m = DATE_RE.match(s)
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%a %b %d %H:%M:%S %Y").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def parse_value(s: str | None) -> float | None:
    s = re.sub(r"[^\d.]", "", s or "")
    try:
        return float(s) if s else None
    except ValueError:
        return None


def parse_list(html: str) -> list[dict]:
    """Rows of the current-opportunities table as raw dicts (strings), keyed by header text."""
    soup = BeautifulSoup(html, "lxml")
    table = None
    for t in soup.find_all("table"):
        heads = [th.get_text(" ", strip=True).lower() for th in t.find_all("th")]
        if any("title" in h for h in heads) and any("deadline" in h or "published" in h for h in heads):
            table = t
            break
    if table is None:
        return []
    headers = [th.get_text(" ", strip=True).lower() for th in table.find_all("th")]
    rows = []
    for tr in table.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 4:
            continue
        row = {}
        for h, td in zip(headers, cells):
            row[h] = td.get_text(" ", strip=True)
            a = td.find("a", href=True)
            if a and "title" in h:
                row["href"] = a["href"]
                row["title"] = a.get_text(" ", strip=True)
            if a and "pdf" in h:
                row["pdf"] = a["href"]
        rows.append(row)
    return rows


def _col(row: dict, *needles: str) -> str | None:
    for k, v in row.items():
        if all(n in k for n in needles):
            return v
    return None


def normalize(row: dict) -> dict | None:
    title = row.get("title") or _col(row, "title")
    href = row.get("href") or ""
    rid = _col(row, "resource") or re.search(r"resourceId=(\d+)", href or "")
    if hasattr(rid, "group"):
        rid = rid.group(1)
    if not title or not rid:
        return None
    url = href if href.startswith("http") else BASE + href if href else LIST_URL
    published = parse_date(_col(row, "published"))
    deadline = parse_date(_col(row, "deadline"))
    return {
        "_id": f"etenders:{rid}", "source": "etenders", "source_id": str(rid),
        "title": title, "description": _col(row, "info") or None, "buyer": _col(row, "ca") or "",
        "cpv": [], "country": "IE", "nuts": [], "place": None,
        "value": parse_value(_col(row, "value")), "currency": "EUR",
        "published_at": published,
        "deadline": deadline.replace(hour=0, minute=0, second=0) if deadline else None,
        "url": url,
        "raw": {"status": _col(row, "status"), "procedure": _col(row, "procedure"), "pdf": row.get("pdf")},
    }


def fetch(since: date, max_pages: int = 8) -> list[dict]:
    out: list[dict] = []
    with httpx.Client(headers=HEADERS, timeout=60, follow_redirects=True) as client:
        for page in range(1, max_pages + 1):
            r = client.get(LIST_URL, params={"currentType": "cft", "d-3680175-p": page})
            r.raise_for_status()
            rows = parse_list(r.text)
            if not rows:
                break
            older = False
            for row in rows:
                t = normalize(row)
                if not t:
                    continue
                if t["published_at"] and t["published_at"].date() < since:
                    older = True
                    continue
                out.append(t)
            if older:
                break
            time.sleep(1)
    return out


def fetch_detail(client: httpx.Client, url: str) -> dict:
    """Optional: the CfT page has CPV codes and a fuller description. Not called by default."""
    r = client.get(url)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    text = soup.get_text(" ", strip=True)
    cpv = re.findall(r"\b(\d{8})-\d\b", text)
    return {"cpv": list(dict.fromkeys(cpv)), "text": text[:4000]}
