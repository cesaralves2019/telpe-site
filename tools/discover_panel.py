"""Find where the TSE "Painel da evolução da totalização" keeps its data.

Runs on GitHub Actions (the sandbox that builds this site cannot reach the TSE). It fetches the
panel's HTML and scripts, collects every URL-looking string that ends in .json/.csv/.zip or lives
under a data-ish path, probes a handful of likely endpoints, and writes data/panel-discovery.json
so the next step (tools/build_r1_march.py) can be written against what really exists.
"""
import json
import os
import re
import sys
import urllib.request
import urllib.error

ROOT = "https://evolucao-totalizacao.tse.jus.br"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "panel-discovery.json")
UA = {"User-Agent": "Mozilla/5.0 (telpe-marcha discovery)"}


def get(url, limit=400_000):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            body = r.read(limit)
            return r.status, r.headers.get("content-type", ""), body
    except urllib.error.HTTPError as e:
        return e.code, "", b""
    except Exception as e:  # noqa: BLE001
        return -1, str(e), b""


def main():
    report = {"root": ROOT, "pages": {}, "scripts": {}, "urls": [], "probes": {}}
    found = set()
    url_re = re.compile(r"""["'`]((?:https?:)?//[^"'`\s]+|/[^"'`\s]*?\.(?:json|csv|zip|js)(?:\?[^"'`\s]*)?|[\w./-]+\.(?:json|csv|zip)(?:\?[^"'`\s]*)?)["'`]""")
    for page in ("/", "/painel/index.html", "/painel/", "/index.html"):
        st, ct, body = get(ROOT + page)
        text = body.decode("utf-8", "replace")
        report["pages"][page] = {"status": st, "type": ct, "bytes": len(body), "head": text[:1500]}
        for m in url_re.findall(text):
            found.add(m)
        for src in re.findall(r"""<script[^>]+src=["']([^"']+)["']""", text):
            js = src if src.startswith("http") else ROOT + ("/painel/" + src if not src.startswith("/") and page.startswith("/painel") else "/" + src.lstrip("/"))
            if js in report["scripts"]:
                continue
            s2, c2, b2 = get(js, 3_000_000)
            t2 = b2.decode("utf-8", "replace")
            hits = sorted(set(url_re.findall(t2)))
            # keep the context around data-looking strings so URL templates (with ${} placeholders) survive
            ctx = [t2[max(0, mm.start() - 160): mm.end() + 160] for mm in re.finditer(r"(json|csv|dados|historico|evolucao|totaliza)", t2, re.I)][:60]
            report["scripts"][js] = {"status": s2, "bytes": len(b2), "url_hits": hits[:200], "contexts": ctx}
            found.update(hits)
    report["urls"] = sorted(found)
    # obvious guesses
    guesses = [
        "/painel/dados/config.json", "/painel/config.json", "/painel/dados/ele-c.json", "/dados/config.json",
        "/painel/data/config.json", "/painel/assets/config.json", "/painel/dados/br/br-c0001-e006257.json",
        "/painel/dados/6257/br.json", "/painel/dados/6257/br-c0001.json", "/api/config", "/api/eleicoes",
    ]
    for g in guesses:
        st, ct, body = get(ROOT + g, 20_000)
        report["probes"][g] = {"status": st, "type": ct, "sample": body[:600].decode("utf-8", "replace")}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print("pages:", {k: v["status"] for k, v in report["pages"].items()})
    print("scripts:", {k: v["status"] for k, v in report["scripts"].items()})
    print("urls:", len(report["urls"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
