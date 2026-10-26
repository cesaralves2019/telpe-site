from datetime import date

from app import matcher
from app.sample_data import sample_tenders

TODAY = date(2026, 10, 12)


def test_sectors_from_cpv_and_words():
    t = {"title": "Grounds maintenance of parks", "description": "", "cpv": ["77310000"]}
    assert "landscaping" in matcher.classify_sectors(t)
    t = {"title": "Website redesign and content management system", "description": "", "cpv": []}
    assert matcher.classify_sectors(t) == {"it"}
    t = {"title": "Security services for civic buildings", "description": "", "cpv": ["79713000"]}
    assert matcher.classify_sectors(t) == {"security"}


def test_regions():
    assert matcher.classify_region({"buyer": "Dublin City Council", "title": "", "nuts": [], "country": "IE"}) == "dublin"
    assert matcher.classify_region({"buyer": "Wexford County Council", "title": "", "nuts": [], "country": "IE"}) == "leinster"
    assert matcher.classify_region({"buyer": "Cork County Council", "title": "", "nuts": [], "country": "IE"}) == "munster"
    assert matcher.classify_region({"buyer": "HSE", "title": "Cleaning, nationwide", "nuts": [], "country": "IE"}) == "ireland"
    assert matcher.classify_region({"buyer": "Belfast City Council", "title": "", "nuts": ["UKN"], "country": "GB"}) == "ni"
    assert matcher.classify_region({"buyer": "Manchester City Council", "title": "", "nuts": ["UKD3"], "country": "GB"}) == "uk"


def test_fit_and_rank_on_sample_data():
    tenders = [dict(t, deadline=t["deadline"].date()) for t in sample_tenders(TODAY)]
    profile = {"sectors": ["landscaping", "cleaning"], "region": "all", "band": "any", "keywords": [], "sub": True}
    ranked = matcher.rank(tenders, profile, TODAY)
    buyers = [t["buyer"] for _, t in ranked]
    assert "Dublin City Council" in buyers and "HSE" in buyers and "Wexford County Council" in buyers
    assert "Belfast City Council" not in buyers  # NI is outside "All of Ireland"
    assert all(f >= 70 for f, _ in ranked)

    dublin_only = matcher.rank(tenders, dict(profile, region="dublin"), TODAY)
    assert {t["region"] for _, t in dublin_only} <= {"dublin", "ireland"}

    uk = matcher.rank(tenders, {"sectors": ["cleaning"], "region": "ie-uk", "band": "any", "keywords": [], "sub": True}, TODAY)
    assert "Belfast City Council" in [t["buyer"] for _, t in uk]


def test_keywords_and_size_change_the_score():
    tenders = [dict(t, deadline=t["deadline"].date()) for t in sample_tenders(TODAY)]
    dcc = next(t for t in tenders if t["buyer"] == "Dublin City Council")
    base = matcher.fit(dcc, {"sectors": ["landscaping"], "region": "all", "band": "any", "keywords": [], "sub": True}, TODAY)
    with_kw = matcher.fit(dcc, {"sectors": ["landscaping"], "region": "all", "band": "any", "keywords": ["parks", "mowing"], "sub": True}, TODAY)
    wrong_size = matcher.fit(dcc, {"sectors": ["landscaping"], "region": "all", "band": "xl", "keywords": [], "sub": True}, TODAY)
    assert with_kw > base > wrong_size
    assert matcher.fit(dcc, {"sectors": ["it"], "region": "all", "band": "any", "keywords": [], "sub": True}, TODAY) is None


def test_sub_threshold_flag():
    assert matcher.is_sub_threshold({"source": "etenders", "value": 90000})
    assert not matcher.is_sub_threshold({"source": "etenders", "value": 900000})
    assert not matcher.is_sub_threshold({"source": "ted", "value": 50000})
    assert matcher.is_sub_threshold({"source": "etenders", "value": None})
