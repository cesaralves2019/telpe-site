"""Check that every link used by the Ireland.gov guides answers (content/ie/*.json -> data/ie/links-report.json).

One request per link, identified, with a pause between requests to the same site. Before touching a site it reads
that site's robots.txt and skips any link the site does not allow for this user agent (reported as "robots").
Nothing is stored from the pages: only the HTTP status.
"""
import datetime as dt
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "content", "ie")
OUT = os.path.join(ROOT, "data", "ie", "links-report.json")
UA = "telpe-concept-bot/1.0 (+https://telpe.ai; link check for an unofficial guide, one request per link)"
MD = re.compile(r"\]\((https?://[^)\s]+)\)")


def links():
    found = {}
    for path in sorted(glob.glob(os.path.join(SRC, "*.json"))):
        for g in json.load(open(path, encoding="utf-8")):
            def add(u, kind):
                found.setdefault(u, {"guides": set(), "kinds": set()})
                found[u]["guides"].add(g["id"])
                found[u]["kinds"].add(kind)
            for _, u in g.get("act", []):
                add(u, "action")
            for _, u in g.get("src", []):
                add(u, "source")
            blob = json.dumps(g, ensure_ascii=False)
            for u in MD.findall(blob):
                add(u, "inline")
    return found


def fetch(url, method):
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, "Accept": "text/html,application/pdf,*/*;q=0.5"})
    with urllib.request.urlopen(req, timeout=35) as r:
        return r.status, r.geturl()


def main():
    found = links()
    robots, last, rows = {}, {}, []
    for url in sorted(found):
        host = urllib.parse.urlsplit(url).netloc
        if host not in robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                req = urllib.request.Request(f"https://{host}/robots.txt", headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=25) as r:
                    rp.parse(r.read().decode("utf-8", "replace").splitlines())
            except urllib.error.HTTPError as e:
                rp = None if e.code in (401, 403) else "open"   # no robots file = no restriction; refused = stay away
            except Exception:  # noqa: BLE001
                rp = "open"
            robots[host] = rp
        rp = robots[host]
        row = {"url": url, "guides": sorted(found[url]["guides"]), "kinds": sorted(found[url]["kinds"])}
        if rp is None or (rp != "open" and not rp.can_fetch(UA, url)):
            row["status"] = "robots"
            rows.append(row)
            continue
        wait = 1.5 - (time.time() - last.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        try:
            try:
                status, final = fetch(url, "HEAD")
            except urllib.error.HTTPError as e:
                if e.code in (400, 403, 404, 405, 501):
                    status, final = fetch(url, "GET")
                else:
                    raise
            row["status"] = status
            if final != url:
                row["final"] = final
        except urllib.error.HTTPError as e:
            row["status"] = e.code
        except Exception as e:  # noqa: BLE001
            row["status"] = "error"
            row["error"] = str(e)[:160]
        last[host] = time.time()
        rows.append(row)
        print(row["status"], url, flush=True)
    ok = sum(1 for r in rows if r["status"] == 200)
    out = {"checked": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "total": len(rows), "ok": ok,
           "problems": [r for r in rows if r["status"] != 200], "all": rows}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("links", len(rows), "ok", ok, "other", len(rows) - ok)
    return 0


if __name__ == "__main__":
    sys.exit(main())
