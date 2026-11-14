"""Put the Ireland.gov guides into index.html (content/ie/*.json -> the block between the GUIDES markers).

python3 tools/ie_build.py          validates the guides and rewrites the data block in index.html
Checks: unique ids, known categories, internal links (#/s/id) that resolve, https links only, life-event sets.
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "content", "ie")
PAGE = os.path.join(ROOT, "index.html")
CHECKED = os.environ.get("CHECKED", "2026-11-14")
CATS = ["travel", "identity", "life", "driving", "immigration", "welfare", "health", "tax", "housing", "education", "work", "justice", "local"]
BEGIN, END = "<!--GUIDES:BEGIN-->", "<!--GUIDES:END-->"
INTERNAL = re.compile(r"\]\(#/s/([a-z0-9\-]+)\)")
EXTERNAL = re.compile(r"\]\((?!#)([^)\s]+)\)")
ANCHOR = re.compile(r"\]\(#([a-z][a-z0-9\-]*)\)")


def main():
    guides = []
    for cat in CATS:
        path = os.path.join(SRC, cat + ".json")
        for g in json.load(open(path, encoding="utf-8")):
            assert g["cat"] == cat, (g["id"], "is filed under", cat)
            guides.append(g)
    extra = {os.path.basename(p)[:-5] for p in glob.glob(os.path.join(SRC, "*.json"))} - set(CATS)
    assert not extra, ("files not in CATS:", extra)
    ids = [g["id"] for g in guides]
    assert len(ids) == len(set(ids)), "duplicate ids"
    errors = []
    for g in guides:
        for key in ("id", "cat", "title", "short", "act", "src"):
            if not g.get(key):
                errors.append((g.get("id"), "missing", key))
        blob = json.dumps(g, ensure_ascii=False)
        for ref in INTERNAL.findall(blob):
            if ref not in ids:
                errors.append((g["id"], "links to unknown guide", ref))
        urls = [u for _, u in g.get("act", [])] + [u for _, u in g.get("src", [])] + EXTERNAL.findall(blob)
        for u in urls:
            if not u.startswith("https://"):
                errors.append((g["id"], "not https", u))
        for anchor in ANCHOR.findall(blob):
            if 'id="%s"' % anchor not in open(PAGE, encoding="utf-8").read():
                errors.append((g["id"], "links to a missing section", anchor))
        if blob.count("**") % 2:
            errors.append((g["id"], "odd number of ** markers"))
    sets = json.load(open(os.path.join(SRC, "sets", "life-events.json"), encoding="utf-8"))
    for s in sets:
        for ref in s["guides"]:
            if ref not in ids:
                errors.append(("life event " + s["id"], "unknown guide", ref))
    if errors:
        for e in errors:
            print("ERROR", *e)
        return 1
    data = {"checked": CHECKED, "guides": guides, "sets": sets}
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/").replace("<!--", "<\\!--")
    page = open(PAGE, encoding="utf-8").read()
    a, b = page.index(BEGIN) + len(BEGIN), page.index(END)
    page = page[:a] + '\n<script type="application/json" id="guides-data">' + blob + "</script>\n" + page[b:]
    page = re.sub(r'(<span data-count="guides">)\d*(</span>)', lambda m: m.group(1) + str(len(guides)) + m.group(2), page)
    open(PAGE, "w", encoding="utf-8").write(page)
    words = sum(len(json.dumps(g, ensure_ascii=False).split()) for g in guides)
    print("guides", len(guides), "life events", len(sets), "data", len(blob) // 1024, "KB", "words ~", words)
    return 0


if __name__ == "__main__":
    sys.exit(main())
