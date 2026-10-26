from datetime import date

from app.sources import contracts_finder, etenders, ted

TED_NOTICE = {
    "publication-number": "696492-2026",
    "publication-date": ["2026-10-09+02:00"],
    "notice-type": "cn-standard",
    "notice-title": {"eng": ["Ireland – Grounds maintenance services – Parks North Central"]},
    "title-proc": {"eng": ["Grounds maintenance of parks and open spaces"]},
    "buyer-name": {"eng": ["Dublin City Council"]},
    "buyer-country": ["IRL"],
    "buyer-city": {"eng": ["Dublin"]},
    "classification-cpv": ["77310000", "77311000"],
    "deadline-receipt-tender-date-lot": ["2026-11-14+01:00"],
    "estimated-value-proc": [420000],
    "estimated-value-cur-proc": ["EUR"],
    "links": {"html": {"ENG": "https://ted.europa.eu/en/notice/-/detail/696492-2026"}},
}


def test_ted_normalize():
    t = ted.normalize(TED_NOTICE)
    assert t["_id"] == "ted:696492-2026" and t["source"] == "ted"
    assert t["title"] == "Grounds maintenance of parks and open spaces"
    assert t["buyer"] == "Dublin City Council" and t["country"] == "IE"
    assert t["cpv"] == ["77310000", "77311000"]
    assert t["value"] == 420000 and t["currency"] == "EUR"
    assert t["deadline"].date() == date(2026, 11, 14)
    assert t["published_at"].date() == date(2026, 10, 9)
    assert t["url"].endswith("696492-2026")
    assert "buyer-country IN (IRL GBR)" in ted.query_for(date(2026, 10, 10))


CF_RELEASE = {
    "ocid": "ocds-b5fd17-1a2b3c",
    "id": "1a2b3c4d-0000-1111-2222-333344445555",
    "date": "2026-10-10T09:30:00Z",
    "tag": ["tender"],
    "buyer": {"name": "Manchester City Council"},
    "tender": {
        "title": "Supply of catering equipment for schools",
        "description": "Commercial kitchen equipment for 18 primary schools.",
        "value": {"amount": 220000, "currency": "GBP"},
        "tenderPeriod": {"endDate": "2026-11-05T12:00:00Z"},
        "items": [{"classification": {"scheme": "CPV", "id": "39220000"},
                   "deliveryAddresses": [{"region": "UKD3"}]}],
        "documents": [{"url": "https://www.contractsfinder.service.gov.uk/Notice/1a2b3c4d-0000-1111-2222-333344445555"}],
    },
}


def test_contracts_finder_normalize():
    t = contracts_finder.normalize(CF_RELEASE)
    assert t["source"] == "contracts_finder" and t["buyer"] == "Manchester City Council"
    assert t["cpv"] == ["39220000"] and t["nuts"] == ["UKD3"] and t["country"] == "GB"
    assert t["value"] == 220000 and t["currency"] == "GBP"
    assert t["deadline"].date() == date(2026, 11, 5)
    assert t["url"].endswith("333344445555")


ETENDERS_HTML = """
<html><body>
<table id="results">
<thead><tr><th>#</th><th>Title</th><th>Resource ID</th><th>CA</th><th>Info</th><th>Date published</th>
<th>Tenders Submission Deadline</th><th>Procedure</th><th>Status</th><th>Notice PDF</th><th>Award date</th>
<th>Estimated value</th><th>Cycle</th></tr></thead>
<tbody>
<tr><td>1</td><td><a href="/epps/cft/prepareViewCftWS.do?resourceId=5540121">Grounds Maintenance Services 2027-2029</a></td>
<td>5540121</td><td>Wexford County Council</td><td title="Mowing and hedging across 20 sites">i</td>
<td>Mon Oct 12 11:03:44 IST 2026</td><td>Mon Nov 09 15:00:00 GMT 2026</td><td>Tender Submission</td><td>Open</td>
<td><a href="/epps/cft/downloadNotice.do?id=1">PDF</a></td><td></td><td>50000.0</td><td>1</td></tr>
<tr><td>2</td><td><a href="/epps/cft/prepareViewCftWS.do?resourceId=5540090">Provision of Security Services</a></td>
<td>5540090</td><td>Irish Defence Forces_1144</td><td>i</td>
<td>Fri Oct 09 16:20:00 IST 2026</td><td>Fri Nov 20 12:00:00 GMT 2026</td><td>Tender Submission</td><td>Open</td>
<td></td><td></td><td>900000.0</td><td>1</td></tr>
</tbody></table></body></html>
"""


def test_etenders_parse_and_normalize():
    rows = etenders.parse_list(ETENDERS_HTML)
    assert len(rows) == 2
    t = etenders.normalize(rows[0])
    assert t["_id"] == "etenders:5540121" and t["source"] == "etenders"
    assert t["title"] == "Grounds Maintenance Services 2027-2029" and t["buyer"] == "Wexford County Council"
    assert t["published_at"].date() == date(2026, 10, 12)
    assert t["deadline"].date() == date(2026, 11, 9)
    assert t["value"] == 50000.0 and t["currency"] == "EUR"
    assert t["url"] == "https://www.etenders.gov.ie/epps/cft/prepareViewCftWS.do?resourceId=5540121"
    assert etenders.parse_date("Mon Oct 12 11:03:44 IST 2026").hour == 11
    assert etenders.parse_date("12/10/2026 11:03").date() == date(2026, 10, 12)
