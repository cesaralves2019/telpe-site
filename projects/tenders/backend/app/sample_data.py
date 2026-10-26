"""The 18 illustrative notices from the telpe.ai mock-up, so the bot can be tried end to end
before any fetcher runs: `python -m app.jobs seed-sample`. Buyers are real public bodies;
the contracts are invented. Deadlines are relative to today."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from . import matcher

ROWS = [
    ("Dublin City Council", "Grounds maintenance of parks and open spaces, North Central Area", ["77310000"], "IE", 420000, "EUR", 19, "etenders",
     "Three years plus two optional extensions. Mowing, hedging and litter across 42 sites. Needs €6.5m public liability and two references of similar scale."),
    ("HSE", "Contract cleaning services, community healthcare facilities, Dublin South", ["90910000"], "IE", 1200000, "EUR", 25, "etenders",
     "Eleven primary-care centres, daily cleaning and periodic deep cleans. HSE infection-control standards; staff Garda vetting required."),
    ("Fingal County Council", "Supply and installation of playground equipment, Swords and Balbriggan", ["45236210", "37535200"], "IE", 310000, "EUR", 12, "etenders",
     "Two playgrounds, design-and-install. EN 1176 certified equipment, 12-month defects period. Site visits the week before closing."),
    ("TU Dublin", "Managed print services, all campuses", ["30120000", "79800000"], "IE", 850000, "EUR", 32, "etenders",
     "Five-year managed print across Grangegorman, Tallaght and Blanchardstown. Device fleet, follow-me printing, quarterly reporting."),
    ("Cork County Council", "Road markings and lining, county-wide, 2027 to 2029", ["45233221"], "IE", 2400000, "EUR", 39, "ted",
     "Three-year framework, three lots by division. Thermoplastic and paint, night working. NRA-approved materials only."),
    ("Galway City Council", "Catering services for City Hall and civic events", ["55520000"], "IE", 180000, "EUR", 16, "etenders",
     "Two-year contract for council meetings and about 30 civic events a year. HACCP required; Irish-sourced produce scored."),
    ("Office of Public Works", "Conservation stonework, Kilkenny Castle west wing", ["45454100"], "IE", 640000, "EUR", 23, "etenders",
     "Repointing and stone replacement on a protected structure. Conservation-accredited contractor; lime mortar only; 40-week programme."),
    ("Department of Education", "Framework for digital-skills training for school leaders", ["80500000"], "IE", 500000, "EUR", 46, "etenders",
     "National framework, four lots by region. Blended delivery, evaluation reports per cohort. Trainers need QQI level 8 or equivalent."),
    ("Limerick City and County Council", "Security services for civic buildings and car parks", ["79713000"], "IE", 720000, "EUR", 29, "etenders",
     "Static guarding and mobile patrols, 24/7 at three sites. PSA licence mandatory; TUPE applies to current staff."),
    ("Iarnród Éireann", "Vegetation management along the rail network, Western region", ["77312000"], "IE", 1500000, "EUR", 37, "ted",
     "Lineside vegetation control, Athlone to Galway and Westport. Rail safety-critical training for all operatives; night possessions."),
    ("Dún Laoghaire-Rathdown County Council", "Website redesign and content management system", ["72413000"], "IE", 140000, "EUR", 18, "etenders",
     "Redesign of the council site on an open-source CMS. WCAG 2.2 AA, Irish-language parity, two years of support."),
    ("Belfast City Council", "Cleaning of leisure centres", ["90910000"], "GB", 950000, "GBP", 31, "contracts_finder",
     "Seven leisure centres, four years. Living Wage required; social-value weighting of 10%."),
    ("Manchester City Council", "Supply of catering equipment for schools", ["39220000"], "GB", 220000, "GBP", 24, "contracts_finder",
     "Commercial kitchen equipment for 18 primary schools, supply and install over the Christmas break."),
    ("Scottish Water", "Engineering consultancy, small projects framework", ["71300000"], "GB", 3000000, "GBP", 44, "contracts_finder",
     "Four-year framework for civil and MEICA design under £500k per project. Chartered engineers; ISO 9001."),
    ("Mayo County Council", "Printing of council publications and signage", ["79800000"], "IE", 90000, "EUR", 15, "etenders",
     "Two-year contract, call-off basis. Annual report, newsletters, outdoor signage. Irish-language proofs required."),
    ("Tusla", "Lease of fleet vehicles, 40 units", ["34110000"], "IE", 1100000, "EUR", 40, "etenders",
     "Four-year operating lease, 40 cars and vans, nationwide delivery. Full maintenance, electric preferred."),
    ("Waterford City and County Council", "Energy consultancy for public-buildings retrofit", ["71314300"], "IE", 260000, "EUR", 22, "etenders",
     "Energy audits and retrofit design for 14 buildings. SEAI-registered assessors; deliverables to 2030 targets."),
    ("Wexford County Council", "Leisure-centre cleaning and caretaking", ["90910000"], "IE", 380000, "EUR", 33, "etenders",
     "Two leisure centres, three years. Early and late shifts; pool-hall cleaning standards."),
]


def sample_tenders(today: date | None = None) -> list[dict]:
    today = today or date.today()
    out = []
    for i, (buyer, title, cpv, country, value, cur, days, source, desc) in enumerate(ROWS, 1):
        d = today + timedelta(days=days)
        t = {
            "_id": f"sample:{i}", "source": source, "source_id": f"sample-{i}", "title": title, "description": desc,
            "buyer": buyer, "cpv": cpv, "country": country, "nuts": ["UKN" if buyer.startswith("Belfast") else ""],
            "place": None, "value": float(value), "currency": cur,
            "published_at": datetime.now(timezone.utc) - timedelta(hours=i),
            "deadline": datetime(d.year, d.month, d.day, tzinfo=timezone.utc),
            "url": {"etenders": "https://www.etenders.gov.ie", "ted": "https://ted.europa.eu",
                    "contracts_finder": "https://www.contractsfinder.service.gov.uk"}[source],
            "raw": {"sample": True},
        }
        out.append(matcher.enrich(t))
    return out
