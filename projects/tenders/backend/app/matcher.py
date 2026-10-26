"""Sectors, regions and the fit score.

A tender document (see sources/) carries: title, description, buyer, cpv (list of
codes), country ("IE"/"GB"), nuts (list), value (float or None), currency, source,
deadline (date), published_at (datetime). This module decides which sectors and
region it belongs to, and how well it fits a user's profile.
"""
from __future__ import annotations

import re
from datetime import date

from . import config

# Shown to users in this order; the number is what they reply with.
SECTORS: dict[str, str] = {
    "construction": "Construction & civil works",
    "cleaning": "Cleaning & facilities",
    "it": "IT & software",
    "consultancy": "Consultancy & engineering",
    "catering": "Catering & food",
    "landscaping": "Landscaping & grounds",
    "transport": "Transport & fleet",
    "security": "Security",
    "training": "Training & education",
    "printing": "Printing & marketing",
}
SECTOR_KEYS = list(SECTORS)

# What the user can choose. "all" = all of Ireland, "ie-uk" = Ireland and UK.
REGION_CHOICES: dict[str, str] = {
    "all": "All of Ireland",
    "dublin": "Dublin",
    "leinster": "Leinster",
    "munster": "Munster",
    "connacht": "Connacht",
    "ulster": "Cavan, Donegal, Monaghan",
    "ni": "Northern Ireland",
    "uk": "UK (England, Scotland, Wales)",
    "ie-uk": "Ireland and UK",
}
REGION_KEYS = list(REGION_CHOICES)
IRELAND = ["dublin", "leinster", "munster", "connacht", "ulster", "ireland"]
# A user choice expands to the tender regions it accepts. "ireland" = national bodies.
REGION_GROUP: dict[str, list[str]] = {
    "dublin": ["dublin", "ireland"],
    "leinster": ["dublin", "leinster", "ireland"],
    "munster": ["munster", "ireland"],
    "connacht": ["connacht", "ireland"],
    "ulster": ["ulster", "ireland"],
    "ni": ["ni"],
    "all": IRELAND,
    "uk": ["uk", "ni"],
    "ie-uk": IRELAND + ["ni", "uk"],
}

VALUE_BANDS: dict[str, str] = {
    "s": "Under €100k",
    "m": "€100k to €500k",
    "l": "€500k to €2m",
    "xl": "Over €2m",
    "any": "Any size",
}
VALUE_KEYS = list(VALUE_BANDS)

# CPV prefixes → sector. First match wins per prefix; a tender can be in several sectors.
CPV_SECTORS: list[tuple[str, str]] = [
    ("7731", "landscaping"), ("7734", "landscaping"), ("773", "landscaping"), ("45112", "landscaping"),
    ("45", "construction"), ("44", "construction"),
    ("909", "cleaning"), ("906", "cleaning"), ("7999", "cleaning"), ("5070", "cleaning"), ("7033", "cleaning"),
    ("72", "it"), ("48", "it"), ("30", "it"),
    ("71", "consultancy"), ("73", "consultancy"), ("794", "consultancy"),
    ("55", "catering"), ("15", "catering"), ("3922", "catering"),
    ("60", "transport"), ("34", "transport"), ("63", "transport"), ("501", "transport"),
    ("7971", "security"), ("35", "security"),
    ("80", "training"),
    ("798", "printing"), ("22", "printing"), ("7934", "printing"),
]

# Words in the title/description → sector, for notices without usable CPV codes (eTenders list page).
KEYWORD_SECTORS: dict[str, list[str]] = {
    "construction": ["construction", "building works", "refurbishment", "roofing", "civil works", "road", "paving",
                     "retrofit", "demolition", "playground", "fit-out", "fit out", "plumbing",
                     "electrical works", "mechanical and electrical", "resurfacing", "footpath", "works contract"],
    "cleaning": ["cleaning", "janitorial", "caretaking", "facilities management", "facility management", "hygiene",
                 "waste collection", "pest control", "window cleaning", "washroom"],
    "it": ["software", "it services", "ict", "website", "websites", "cms", "cloud", "hosting", "cyber", "network", "licences",
           "licenses", "managed print", "microsoft", "digital platform", "app development", "it support", "data centre",
           "erp", "crm", "saas"],
    "consultancy": ["consultancy", "consultant", "engineering services", "design services", "architect",
                    "quantity surveyor", "feasibility", "audit", "advisory", "project management", "surveying",
                    "energy audit", "design team", "technical assistance"],
    "catering": ["catering", "canteen", "food", "meals", "kitchen", "vending", "hospitality", "coffee"],
    "landscaping": ["grounds maintenance", "landscaping", "landscape", "grass", "mowing", "hedge", "tree",
                    "vegetation", "parks", "horticultural", "horticulture", "planting", "grounds", "pitch maintenance", "trees"],
    "transport": ["transport", "fleet", "vehicles", "vehicle", "bus", "buses", "haulage", "courier", "logistics",
                  "lease of cars", "vans", "taxi", "minibus"],
    "security": ["security", "guarding", "cctv", "alarm", "access control", "patrol", "manned"],
    "training": ["training", "education", "course", "tuition", "workshop", "learning", "coaching", "upskilling",
                 "e-learning", "apprentice"],
    "printing": ["printing", "print", "signage", "marketing", "advertising", "design and print", "publications",
                 "branding", "media buying", "photography", "video production", "communications campaign"],
}

LEINSTER = ["carlow", "kildare", "kilkenny", "laois", "longford", "louth", "meath", "offaly", "westmeath", "wexford",
            "wicklow", "drogheda", "dundalk", "naas", "athlone", "tullamore", "portlaoise", "mullingar"]
MUNSTER = ["clare", "cork", "kerry", "limerick", "tipperary", "waterford", "ennis", "tralee", "killarney", "clonmel",
           "shannon"]
CONNACHT = ["galway", "leitrim", "mayo", "roscommon", "sligo", "castlebar", "westport"]
ULSTER_IE = ["cavan", "donegal", "monaghan", "letterkenny"]
DUBLIN = ["dublin", "dún laoghaire", "dun laoghaire", "fingal", "swords", "tallaght", "blanchardstown", "balbriggan",
          "dlr "]
NI = ["northern ireland", "belfast", "derry", "londonderry", "armagh", "antrim", "fermanagh", "tyrone",
      "lisburn", "newry", "causeway coast", "mid ulster", "ards and north down", "enniskillen", "omagh"]


def _word_regex(words: list[str]) -> re.Pattern:
    """Whole words only, so "road" doesn't match "broad" and "bus" doesn't match "business"."""
    return re.compile(r"\b(" + "|".join(re.escape(w.strip()) for w in words) + r")\b", re.I)


KEYWORD_REGEX = {sector: _word_regex(words) for sector, words in KEYWORD_SECTORS.items()}


def classify_sectors(tender: dict) -> set[str]:
    found: set[str] = set()
    for code in tender.get("cpv") or []:
        code = str(code).strip()
        for prefix, sector in CPV_SECTORS:
            if code.startswith(prefix):
                found.add(sector)
                break
    if found:
        return found  # codes are more reliable than words; only fall back when there are none
    text = f"{tender.get('title', '')} {tender.get('description', '')}"
    for sector, rx in KEYWORD_REGEX.items():
        if rx.search(text):
            found.add(sector)
    return found


def classify_region(tender: dict) -> str:
    """One region per tender: dublin | leinster | munster | connacht | ulster | ireland | ni | uk."""
    nuts = " ".join(tender.get("nuts") or []).upper()
    country = (tender.get("country") or "").upper()
    text = f"{tender.get('buyer', '')} {tender.get('title', '')} {tender.get('place', '')}".lower()
    if "UKN" in nuts or any(w in text for w in NI):
        return "ni"
    if country in ("GB", "UK", "GBR") or nuts.startswith("UK") or tender.get("source") in ("contracts_finder", "find_a_tender", "pcs"):
        return "uk"
    if "IE061" in nuts or any(w in text for w in DUBLIN):
        return "dublin"
    if any(w in text for w in LEINSTER):
        return "leinster"
    if any(w in text for w in MUNSTER):
        return "munster"
    if any(w in text for w in CONNACHT):
        return "connacht"
    if any(w in text for w in ULSTER_IE):
        return "ulster"
    return "ireland"


def value_band(value: float | None) -> str | None:
    if value is None:
        return None
    return "s" if value < 100_000 else "m" if value < 500_000 else "l" if value < 2_000_000 else "xl"


def is_sub_threshold(tender: dict) -> bool:
    """Below the EU services threshold, so it will never appear on TED. Heuristic."""
    value = tender.get("value")
    source = tender.get("source")
    if source == "ted":
        return False
    if source in ("contracts_finder",):
        return value is not None and value < 214_904  # UK sub-central services threshold (GBP)
    return value is None or value < 221_000  # EU sub-central services threshold (EUR), 2026-27


def enrich(tender: dict) -> dict:
    """Add the derived fields once, at fetch time, so matching is cheap."""
    tender["sectors"] = sorted(classify_sectors(tender))
    tender["region"] = classify_region(tender)
    tender["band"] = value_band(tender.get("value"))
    tender["sub"] = is_sub_threshold(tender)
    return tender


def keywords_from(text: str | None) -> list[str]:
    return [w for w in re.split(r"[,\s;]+", (text or "").lower()) if len(w) > 2]


def fit(tender: dict, profile: dict, today: date | None = None) -> int | None:
    """0–100, or None when the tender is out of scope for this profile.

    profile: {sectors: [...], region: "dublin"|..., band: "any"|"s"|..., keywords: [...], sub: bool}
    """
    today = today or date.today()
    sectors = set(profile.get("sectors") or [])
    t_sectors = set(tender.get("sectors") or [])
    if sectors and not (sectors & t_sectors):
        return None
    if tender.get("region") not in REGION_GROUP.get(profile.get("region") or "all", IRELAND):
        return None
    if tender.get("sub") and not profile.get("sub", True):
        return None
    # sector 55 + region 15 are given (we returned None otherwise); the rest spreads the scores:
    # size exact +10 / any +5 / unknown 0 / wrong −25; keywords up to +15, or −10 if none hit;
    # CPV-classified +3; closing within 3 days −10. A plain sector+region match lands at 78.
    score = 55 + 15
    band = profile.get("band") or "any"
    if band == "any":
        score += 5
    elif tender.get("band") == band:
        score += 10
    elif tender.get("band") is not None:
        score -= 25
    kws = profile.get("keywords") or []
    if kws:
        hay = f"{tender.get('title', '')} {tender.get('description', '')} {tender.get('buyer', '')}".lower()
        hits = [w for w in kws if w in hay]
        score += min(15, 8 * len(hits))
        if not hits:
            score -= 10
    deadline = tender.get("deadline")
    if deadline is not None and (deadline - today).days <= 3:
        score -= 10
    if tender.get("cpv"):
        score += 3  # classified from codes rather than words: a little more trust
    return max(35, min(98, score))


def best_sector(tender: dict, profile: dict) -> str:
    """The user's sector this tender matched, for the 'Fit 92% for landscaping' line."""
    common = [s for s in profile.get("sectors") or [] if s in (tender.get("sectors") or [])]
    key = common[0] if common else (tender.get("sectors") or ["general"])[0]
    return SECTORS.get(key, key)


def rank(tenders: list[dict], profile: dict, today: date | None = None, min_fit: int | None = None) -> list[tuple[int, dict]]:
    min_fit = config.MIN_FIT if min_fit is None else min_fit
    scored = []
    for t in tenders:
        f = fit(t, profile, today)
        if f is not None and f >= min_fit:
            scored.append((f, t))
    scored.sort(key=lambda x: (-x[0], x[1].get("deadline") or date.max))
    return scored
