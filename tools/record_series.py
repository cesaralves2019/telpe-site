"""Append the current national totals of the runoff to data/series.json, once per TSE batch.

Runs on GitHub Actions every 5 minutes on election night (.github/workflows/marcha.yml);
the page merges this file with the batches each browser sees itself, so every visitor
gets the whole curve, not just the part they watched.
"""
import json
import os
import sys
import base64
import urllib.request

ELE = os.environ.get("ELE", "6258")
URL = f"https://resultados.tse.jus.br/oficial/ele2026/{ELE}/dados/br/br-c0001-e{int(ELE):06d}-u.json"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "series.json")


def num(s):
    if s is None or s == "":
        return 0.0
    if isinstance(s, (int, float)):
        return float(s)
    t = str(s).strip()
    return float(t.replace(".", "").replace(",", ".")) if "," in t else float(t)


def fetch(url):
    import time as _t
    url = url + ("&" if "?" in url else "?") + "t=" + str(int(_t.time()))   # past the CDN cache
    req = urllib.request.Request(url, headers={"User-Agent": "telpe-marcha/1.0", "Cache-Control": "no-cache", "Pragma": "no-cache"})
    with urllib.request.urlopen(req, timeout=40) as r:
        raw = r.read().decode("utf-8")
    try:
        return json.loads(raw)
    except ValueError:  # JWS: header.payload.signature
        payload = raw.strip().split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload).decode("utf-8"))


UFS = "ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc sp se to zz".split()
LIVE_DIR = os.path.join(os.path.dirname(OUT), "live")


def snapshot():
    """Also keep the latest national and state files in data/live/, so the count can be inspected from the repo."""
    os.makedirs(LIVE_DIR, exist_ok=True)
    for abr in ["br"] + UFS:
        url = f"https://resultados.tse.jus.br/oficial/ele2026/{ELE}/dados/{abr}/{abr}-c0001-e{int(ELE):06d}-u.json"
        try:
            j = fetch(url)
        except Exception as e:  # noqa: BLE001
            print("snapshot failed", abr, e)
            continue
        with open(os.path.join(LIVE_DIR, f"{abr}.json"), "w", encoding="utf-8") as f:
            json.dump(j, f, ensure_ascii=False, separators=(",", ":"))
    # the first-round files once (they do not change): the page's prior, kept here for offline checks of the model
    r1_dir = os.path.join(os.path.dirname(OUT), "r1")
    os.makedirs(r1_dir, exist_ok=True)
    for abr in ["br"] + UFS:
        dest = os.path.join(r1_dir, f"{abr}.json")
        if os.path.exists(dest):
            continue
        try:
            j = fetch(f"https://resultados.tse.jus.br/oficial/ele2026/6257/dados/{abr}/{abr}-c0001-e006257-u.json")
        except Exception as e:  # noqa: BLE001
            print("r1 snapshot failed", abr, e)
            continue
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(j, f, ensure_ascii=False, separators=(",", ":"))


def status(**kw):
    os.makedirs(LIVE_DIR, exist_ok=True)
    import datetime as _dt
    kw["at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    with open(os.path.join(LIVE_DIR, "status.json"), "w", encoding="utf-8") as f:
        json.dump(kw, f, ensure_ascii=False)


def main():
    try:
        j = fetch(URL)
    except Exception as e:  # keep the workflow green; the next run retries
        print("fetch failed:", e)
        status(error=str(e)[:300])
        return 0
    status(hg=str(j.get("hg") or ""), pst=(j.get("s") or {}).get("pst"), dt=j.get("dt"), ht=j.get("ht"))
    try:
        snapshot()
    except Exception as e:  # noqa: BLE001
        print("snapshot error:", e)
    s = j.get("s") or {}
    hg = str(j.get("hg") or "")[:8]
    st = num(s.get("st"))
    if not hg or st <= 0:
        print("no totals yet", hg, st)
        return 0
    cands = {}
    for a in (j.get("carg") or [{}])[0].get("agr") or []:
        for p in a.get("par") or []:
            for c in p.get("cand") or []:
                cands[str(c.get("n"))] = {"p": num(c.get("pvap")), "v": int(num(c.get("vap")))}
    if not cands or not any(c["v"] > 0 for c in cands.values()):
        print("zeroed", hg)
        return 0
    series = []
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            try:
                series = json.load(f)
            except ValueError:
                series = []
    if any(p.get("hg") == hg for p in series):
        print("already have", hg)
        return 0
    series.append({"hg": hg, "dg": j.get("dg"), "pst": num(s.get("pst")), "c": cands})
    series.sort(key=lambda p: p["hg"])
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(series, f, ensure_ascii=False, separators=(",", ":"))
    print("recorded", hg, num(s.get("pst")), {k: v["p"] for k, v in cands.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
