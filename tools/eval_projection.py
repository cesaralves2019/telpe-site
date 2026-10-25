"""Offline check of the page's projection on the files the recorder keeps in data/ (same arithmetic as index.html).

python3 tools/eval_projection.py            -> national projection, swing, per-state detail
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UFS = "ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc sp se to zz".split()
A, B = "13", "22"
POLL_A = 49.0  # Datafolha 23-24 Oct, valid votes for candidate 13
PHI = float(os.environ.get("PHI", "0.5"))  # share of the first-round within-state correction applied


def num(s):
    if s is None or s == "":
        return 0.0
    t = str(s).strip()
    return float(t.replace(".", "").replace(",", ".")) if "," in t else float(t)


def parse(j):
    cands = {}
    for a in (j.get("carg") or [{}])[0].get("agr") or []:
        for p in a.get("par") or []:
            for c in p.get("cand") or []:
                cands[str(c.get("n"))] = int(num(c.get("vap")))
    s = j.get("s") or {}
    v = j.get("v") or {}
    return {"cands": cands, "pst": num(s.get("pst")), "valid": num(v.get("vv")), "hg": j.get("hg")}


def load(d):
    out = {}
    for uf in UFS:
        p = os.path.join(ROOT, "data", d, f"{uf}.json")
        if os.path.exists(p):
            out[uf] = parse(json.load(open(p, encoding="utf-8")))
    return out


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def main():
    r1 = load("r1")
    live = load("live")
    march = json.load(open(os.path.join(ROOT, "data", "r1-march.json"), encoding="utf-8"))
    bench, fin = march.get("bench", {}), march.get("fin", {})
    br = parse(json.load(open(os.path.join(ROOT, "data", "live", "br.json"), encoding="utf-8")))
    rows = []
    for uf in UFS:
        p = r1.get(uf)
        if not p or (p["cands"].get(A, 0) + p["cands"].get(B, 0)) == 0:
            continue
        pa, pb = p["cands"][A], p["cands"][B]
        pri = pa / (pa + pb)
        V = p["valid"]
        x = live.get(uf)
        ca = cb = 0
        w = 0.0
        run = adj = None
        has_b = False
        if x and x["cands"].get(A, 0) + x["cands"].get(B, 0) > 0:
            ca, cb = x["cands"][A], x["cands"][B]
            t = ca + cb
            w = clamp(x["pst"] / 100, 0, 1)
            run = ca / t
            b = bench.get(uf)
            if b:
                has_b = True
                k = int(round(w * 100))
                adj = clamp(run + PHI * (fin.get(uf, pri) - b[clamp(k, 0, 100)]), 0.02, 0.98)
        rows.append({"uf": uf, "V": V, "pri": pri, "ca": ca, "cb": cb, "w": w, "run": run, "adj": adj, "hb": has_b})
    totalV = sum(r["V"] for r in rows)
    r1br = parse(json.load(open(os.path.join(ROOT, "data", "r1", "br.json"), encoding="utf-8")))
    nat2 = r1br["cands"][A] / (r1br["cands"][A] + r1br["cands"][B])
    swing0 = POLL_A / 100 - nat2
    kappa = 0.03 * totalV
    num_ = den = 0.0
    for r in rows:
        r["lam"] = 0.0
        r["est"] = None
        if r["run"] is not None:
            r["lam"] = clamp((r["w"] - 0.005) / 0.05, 0, 1) if r["hb"] else r["w"]
            r["est"] = r["adj"] if r["hb"] else r["run"]
            if r["lam"] > 0:
                wt = (r["ca"] + r["cb"]) * r["lam"]
                num_ += (r["est"] - r["pri"]) * wt
                den += wt
    swing = (num_ + kappa * swing0) / (den + kappa)
    print(f"poll-implied swing {100*swing0:+.2f} pp · data weight {den/(den+kappa):.3f}")
    sumA = sumV = counted = 0.0
    for r in rows:
        base = clamp(r["pri"] + swing, 0.02, 0.98)
        r["share"] = base if r["est"] is None else clamp(r["lam"] * r["est"] + (1 - r["lam"]) * base, 0.02, 0.98)
        sumA += r["V"] * r["share"]
        sumV += r["V"]
        counted += r["ca"] + r["cb"]
    pctA = 100 * sumA / sumV
    tot = br["cands"].get(A, 0) + br["cands"].get(B, 0)
    print(f"BR file {br['hg']}: counted {br['pst']:.2f}% sections, raw {A} {100*br['cands'].get(A,0)/tot:.2f}% × {B} {100*br['cands'].get(B,0)/tot:.2f}%")
    print(f"projection {A} {pctA:.2f}% × {B} {100-pctA:.2f}%  | swing {100*swing:+.2f} pp | counted {100*counted/sumV:.2f}% of expected two-way votes | bench {'yes' if bench else 'no'}")
    print(f"{'uf':<3}{'pri':>7}{'w%':>7}{'run':>7}{'adj':>7}{'lam':>6}{'share':>8}{'votes':>12}")
    for r in sorted(rows, key=lambda r: -r["V"]):
        f = lambda v: "   -" if v is None else f"{100*v:6.1f}"
        print(f"{r['uf']:<3}{100*r['pri']:7.1f}{100*r['w']:7.2f}{f(r['run']):>7}{f(r['adj']):>7}{r['lam']:6.2f}{100*r['share']:8.1f}{int(r['ca']+r['cb']):12,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
