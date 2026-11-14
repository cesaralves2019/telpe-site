"""List every service page that gov.ie itself lists at https://www.gov.ie/en/services/ (title, link, department).

The Ireland.gov concept keeps full plain-language guides for the services people use most; for everything else it
only needs the official title and link, so the search can send people to the right gov.ie page. This walks the
public listing page by page and writes data/ie/govie-services.json.

Rules it follows:
  - reads https://www.gov.ie/robots.txt first and stops if the listing is disallowed for this user agent;
  - identifies itself, waits between requests (the site's crawl-delay if it sets one, otherwise 2 seconds);
  - only titles and links are kept, nothing else from the pages.
gov.ie content is published for re-use under CC BY 4.0 (Irish Public Sector Information licence).
"""
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import urllib.robotparser

BASE = "https://www.gov.ie"
LISTING = BASE + "/en/services/"
UA = "telpe-concept-bot/1.0 (+https://telpe.ai; unofficial concept, lists public service titles and links)"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "ie", "govie-services.json")
MAX_PAGES = int(os.environ.get("MAX_PAGES", "220"))

LINK = re.compile(r'<a\b[^>]*?href="((?:https://www\.gov\.ie)?/en/([a-z0-9\-%]+)/services/([^"/?#]+)/?)"[^>]*>(.*?)</a>', re.I | re.S)
TAG = re.compile(r"<[^>]+>")
SPACE = re.compile(r"\s+")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")


def org_name(slug):
    words = slug.replace("-", " ").split()
    small = {"of", "and", "the", "for", "to", "in"}
    return " ".join(w if w in small and i else w.capitalize() for i, w in enumerate(words))


def main():
    rp = urllib.robotparser.RobotFileParser()
    try:
        rp.parse(get(BASE + "/robots.txt").splitlines())
    except Exception as e:  # noqa: BLE001
        print("could not read robots.txt:", e, "- stopping, nothing collected")
        return 0
    if not rp.can_fetch(UA, LISTING) or not rp.can_fetch(UA, LISTING + "?page=2"):
        print("robots.txt does not allow this listing for our user agent - stopping, nothing collected")
        return 0
    delay = rp.crawl_delay(UA) or 2
    print("robots.txt allows the listing; delay between requests:", delay, "s", flush=True)

    items, seen, empty = [], set(), 0
    for page in range(1, MAX_PAGES + 1):
        url = LISTING if page == 1 else f"{LISTING}?page={page}"
        try:
            body = get(url)
        except urllib.error.HTTPError as e:
            print("page", page, "HTTP", e.code, "- stopping here", flush=True)
            break
        except Exception as e:  # noqa: BLE001
            print("page", page, "failed:", e, "- stopping here", flush=True)
            break
        new = 0
        for m in LINK.finditer(body):
            href, org, slug, inner = m.group(1), m.group(2), m.group(3), m.group(4)
            title = SPACE.sub(" ", html.unescape(TAG.sub(" ", inner))).strip()
            if not title or len(title) > 240:
                continue
            path = href.replace(BASE, "")
            if not path.endswith("/"):
                path += "/"
            if path in seen:
                continue
            seen.add(path)
            items.append([title, path, org])
            new += 1
        print("page", page, "new", new, "total", len(items), flush=True)
        if new == 0:
            empty += 1
            if empty >= 2:
                break
        else:
            empty = 0
        time.sleep(delay)

    if len(items) < 50:
        print("only", len(items), "links found - the page layout may have changed; not writing the file")
        return 1
    orgs = {}
    for _, _, o in items:
        orgs.setdefault(o, org_name(o))
    items.sort(key=lambda x: x[0].lower())
    out = {
        "fetched": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": LISTING,
        "licence": "Contains Irish Public Sector Information licensed under a Creative Commons Attribution 4.0 International (CC BY 4.0) licence.",
        "base": BASE,
        "count": len(items),
        "orgs": orgs,
        "items": items,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("wrote", OUT, "services", len(items), "departments", len(orgs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
