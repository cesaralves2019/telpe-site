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
    req = urllib.request.Request(url, headers={"User-Agent": "telpe-marcha/1.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        raw = r.read().decode("utf-8")
    try:
        return json.loads(raw)
    except ValueError:  # JWS: header.payload.signature
        payload = raw.strip().split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload).decode("utf-8"))


def main():
    try:
        j = fetch(URL)
    except Exception as e:  # keep the workflow green; the next run retries
        print("fetch failed:", e)
        return 0
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
