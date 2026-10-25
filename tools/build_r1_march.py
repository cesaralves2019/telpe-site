"""Rebuild the march of the FIRST-round count from the TSE's open data, to data/r1-march.json.

The TSE publishes every ballot-box bulletin (boletim de urna) of the first round as open data,
with the exact time each one reached the totalization system (DT_BU_RECEBIDO). Summing those
minute by minute reproduces how the national percentages and every state's progress moved on
4 October 2026 — the real timetable the page uses to shape tonight's projections and the
chart's time axis. Runs on GitHub Actions (.github/workflows/r1-march.yml); the sandbox that
builds the site has no network.

Output (minutes are counted from 17:00 Brasília of election day):
  {"built": iso, "source": [...], "cands": ["13","22"], "endMin": 345, "lastMin": 1480,
   "sections": 496000, "br": [{"tm": 7, "a": 44.1, "b": 50.2, "pst": 0.4}, ...],
   "uf": {"ac": [[0,0],[5,0.01],...], ...}}
  endMin = minute at which END_SHARE of all sections had been received (the chart's right edge),
  lastMin = the very last bulletin.
"""
import datetime as dt
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

CKAN = "https://dadosabertos.tse.jus.br/api/3/action/"
DATASETS = ["resultados-2026-boletim-de-urna", "resultados-2026"]
UFS = "ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc sp se to zz".split()
ELECTION_DAY = dt.date(2026, 10, 4)
CANDS = ("13", "22")
END_SHARE = float(os.environ.get("END_SHARE", "0.999"))
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "r1-march.json")
UA = {"User-Agent": "Mozilla/5.0 (telpe-marcha; +https://telpe.ai)"}


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def find_resources():
    """Map UF -> zip URL of the first-round bulletin file."""
    found = {}
    for ds in DATASETS:
        try:
            pkg = get_json(CKAN + "package_show?id=" + ds)["result"]
        except Exception as e:  # noqa: BLE001
            print("package_show", ds, "failed:", e)
            continue
        for res in pkg.get("resources") or []:
            url = res.get("url") or ""
            name = (res.get("name") or "") + " " + url
            m = re.search(r"bweb_1t_([A-Z]{2})_\d+\.zip", name)
            if m:
                found.setdefault(m.group(1).lower(), url)
        if found:
            break
    if not found:  # last resort: search
        try:
            hits = get_json(CKAN + "package_search?q=boletim+urna+2026&rows=20")["result"]["results"]
            for pkg in hits:
                for res in pkg.get("resources") or []:
                    url = res.get("url") or ""
                    m = re.search(r"bweb_1t_([A-Z]{2})_\d+\.zip", url)
                    if m:
                        found.setdefault(m.group(1).lower(), url)
        except Exception as e:  # noqa: BLE001
            print("package_search failed:", e)
    return found


def download(url, dest):
    subprocess.run(["curl", "-sSL", "--retry", "3", "--retry-delay", "5", "-A", UA["User-Agent"], "-o", dest, url], check=True)


def csv_member(zip_path):
    names = subprocess.run(["unzip", "-Z1", zip_path], capture_output=True, text=True, check=True).stdout.split()
    csvs = [n for n in names if n.lower().endswith(".csv")]
    if not csvs:
        raise SystemExit(f"{zip_path}: no csv inside ({names[:5]})")
    return max(csvs, key=len)


def header_of(zip_path):
    out = subprocess.run("unzip -p %s '%s' | head -c 8192" % (zip_path, csv_member(zip_path)), shell=True, capture_output=True, check=False).stdout
    line = out.split(b"\n", 1)[0].decode("latin-1")
    return [c.strip().strip('"') for c in line.split(";")]


def process(uf, zip_path, acc):
    cols = header_of(zip_path)
    idx = {c: i for i, c in enumerate(cols)}
    need = ["DT_BU_RECEBIDO", "NR_VOTAVEL", "QT_VOTOS", "CD_TIPO_VOTAVEL", "NR_ZONA", "NR_SECAO", "DS_CARGO_PERGUNTA"]
    missing = [c for c in need if c not in idx]
    if missing:
        raise SystemExit(f"{uf}: columns missing {missing}; header was {cols[:40]}")
    i_dt, i_nr, i_qt, i_tp, i_zn, i_sc, i_cg = (idx[c] for c in need)
    i_mun = idx.get("CD_MUNICIPIO")
    stamp_br = re.compile(r"(\d\d)/(\d\d)/(\d{4}) (\d\d):(\d\d)(?::(\d\d))?")      # 04/10/2026 17:40:20
    stamp_iso = re.compile(r"(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d)(?::(\d\d))?")     # 2026-10-04 17:40:20 (the 2026 files)
    # grep keeps only the president's rows; the CSV is latin-1 and ';'-separated with quoted fields
    cmd = "unzip -p %s '%s' | grep -a -i -F presidente" % (zip_path, csv_member(zip_path))
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    per_min = acc["uf"].setdefault(uf, {})
    seen = acc["sections_seen"]
    br = acc["br"]
    n = 0
    for raw in io.TextIOWrapper(proc.stdout, encoding="latin-1", newline=""):
        f = raw.rstrip("\r\n").split(";")
        if len(f) <= max(i_dt, i_nr, i_qt, i_tp, i_zn, i_sc, i_cg):
            continue
        if f[i_cg].strip('"').strip().upper() != "PRESIDENTE":
            continue
        m = stamp_iso.search(f[i_dt])
        if m:
            d = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        else:
            m = stamp_br.search(f[i_dt])
            if not m:
                continue
            d = dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        tm = (d - ELECTION_DAY).days * 1440 + int(m.group(4)) * 60 + int(m.group(5)) - 17 * 60
        if tm < 0:
            tm = 0
        tp = f[i_tp].strip('"')
        nr = f[i_nr].strip('"')
        try:
            q = int(f[i_qt].strip('"'))
        except ValueError:
            q = 0
        slot = br.setdefault(tm, {"13": 0, "22": 0, "valid": 0})
        um = per_min.setdefault(tm, [0, 0, 0])  # [votes 13, votes 22, sections] of this state in this minute
        if tp == "1":  # nominal vote
            slot["valid"] += q
            if nr == CANDS[0]:
                slot[nr] += q
                um[0] += q
            elif nr == CANDS[1]:
                slot[nr] += q
                um[1] += q
        key = (uf, f[i_mun].strip('"') if i_mun is not None else "", f[i_zn].strip('"'), f[i_sc].strip('"'))
        if key not in seen:
            seen.add(key)
            slot["sec"] = slot.get("sec", 0) + 1
            um[2] += 1
        n += 1
    proc.wait()
    print(uf, "rows", n, "sections so far", len(seen), flush=True)
    if n == 0:  # show what the file really looks like, so the next run can be fixed from the log
        sample = subprocess.run("unzip -p %s '%s' | head -n 4" % (zip_path, csv_member(zip_path)), shell=True, capture_output=True, check=False).stdout.decode("latin-1", "replace")
        print(uf, "HEADER/SAMPLE:", sample[:3000].replace("\n", "\n  "), flush=True)
        cargos = subprocess.run("unzip -p %s '%s' | head -n 200000 | cut -d';' -f%d | sort | uniq -c | sort -rn | head -12" % (zip_path, csv_member(zip_path), i_cg + 1), shell=True, capture_output=True, check=False).stdout.decode("latin-1", "replace")
        print(uf, "CARGOS:", cargos, flush=True)


def build(acc):
    br = acc["br"]
    if not br:
        raise SystemExit("no rows parsed")
    total_sec = len(acc["sections_seen"])
    times = sorted(br)
    last_min = times[-1]
    cum = {"13": 0, "22": 0, "valid": 0, "sec": 0}
    series = []
    end_min = None
    # one point per minute with data, carrying the cumulative figures
    for tm in times:
        s = br[tm]
        for k in ("13", "22", "valid"):
            cum[k] += s[k]
        cum["sec"] += s.get("sec", 0)
        if cum["valid"] > 0:
            series.append({"tm": tm, "a": round(100 * cum["13"] / cum["valid"], 3), "b": round(100 * cum["22"] / cum["valid"], 3), "pst": round(100 * cum["sec"] / total_sec, 2)})
        if end_min is None and total_sec and cum["sec"] / total_sec >= END_SHARE:
            end_min = tm
    if end_min is None:
        end_min = last_min
    end_min = int(min(max(180, -(-end_min // 30) * 30), 24 * 60))  # round up to the half hour, at least 20:00
    series = [p for p in series if p["tm"] <= end_min]
    uf_curves, bench, fin = {}, {}, {}
    for uf, per_min in acc["uf"].items():
        tot = sum(v[0] + v[1] for v in per_min.values())
        tot_sec = sum(v[2] for v in per_min.values())
        if not tot or not tot_sec:
            continue
        keys = sorted(per_min)
        # arrival curve in time (share of the state's two-way votes counted every 5 minutes), for the chart
        pts, c, j = [], 0, 0
        for tm in range(0, end_min + 1, 5):
            while j < len(keys) and keys[j] <= tm:
                c += per_min[keys[j]][0] + per_min[keys[j]][1]
                j += 1
            pts.append([tm, round(c / tot, 4)])
        uf_curves[uf] = pts
        # benchmark: the running two-way share of candidate 13 when k% of the state's sections were in (k = 0..100)
        a = b = sec = 0
        run = []  # (sections fraction, running share)
        for tm in keys:
            v = per_min[tm]
            a += v[0]
            b += v[1]
            sec += v[2]
            if a + b:
                run.append((sec / tot_sec, a / (a + b)))
        final = a / (a + b)
        curve, i = [], 0
        for k in range(101):
            target = k / 100
            while i < len(run) - 1 and run[i][0] < target:
                i += 1
            curve.append(round(run[i][1], 4))
        bench[uf] = curve
        fin[uf] = round(final, 4)
    return {"built": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "source": acc["source"], "cands": list(CANDS), "endShare": END_SHARE,
            "endMin": end_min, "lastMin": last_min, "sections": total_sec, "br": series, "uf": uf_curves, "bench": bench, "fin": fin,
            "benchNote": "bench[uf][k] = share of candidate 13 among the two finalists when k% of the state's sections had reached the totalization in the first round; fin[uf] = final share"}


def main():
    res = find_resources()
    print("resources:", len(res), sorted(res))
    if not res:
        raise SystemExit("no bweb_1t files found in the open-data catalogue")
    acc = {"br": {}, "uf": {}, "sections_seen": set(), "source": []}
    only = [u for u in os.environ.get("ONLY", "").lower().split() if u]
    with tempfile.TemporaryDirectory() as tmp:
        for uf in UFS:
            if only and uf not in only:
                continue
            url = res.get(uf)
            if not url:
                print(uf, "missing in catalogue")
                continue
            zp = os.path.join(tmp, f"{uf}.zip")
            print(uf, "downloading", url, flush=True)
            download(url, zp)
            print(uf, "size", os.path.getsize(zp) // 1_000_000, "MB", flush=True)
            process(uf, zp, acc)
            acc["source"].append(url)
            os.remove(zp)
    out = build(acc)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("wrote", OUT, "points", len(out["br"]), "endMin", out["endMin"], "lastMin", out["lastMin"], "sections", out["sections"])
    if out["br"]:
        print("first", out["br"][0], "last", out["br"][-1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
