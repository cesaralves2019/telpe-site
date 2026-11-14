# Ireland.gov concept — working notes (kept so the work can be resumed)

Request (site owner, 14 Nov 2026): inside the mock-up, bring the real public services of Ireland, validated and
cross-checked against official sources, with working links; easy for anyone (foreigner or Irish). "Everything on gov.ie".
Rules he set: public information may be copied; do NOT scrape a site that says scraping is not allowed
(robots.txt / terms). gov.ie and citizensinformation.ie re-use terms checked 14 Nov 2026: CC BY 4.0, attribution
required ("Contains Irish Public Sector Information licensed under CC BY 4.0"); no ban on automated access found.

## Content model (content/ie/*.json — arrays of guides)
id, cat, title, kw (extra search words, incl. a few Portuguese), short, facts [[label,value]], who [], need [],
steps [], cases [{q, a:[]}], tips [], act [[label,url]], src [[label,url]] (ONLY pages actually read today).
Inline markup in strings: **bold**, [text](url), [text](#/s/guide-id) for internal links.
Categories: travel, identity, life, driving, immigration, welfare, health, tax, housing, education, work, justice, local.

## Done (files written, facts read on 14 Nov 2026)
travel.json (6 passport guides), identity.json (psc, ppsn, mygovid, certificates), life.json (birth, marriage, death),
driving.json (first licence, exchange, renew, motor tax, nct, ownership), immigration.json (irp-register, irp-renew,
visa, work-permit, citizenship, citizenship-fbr, eu-citizens).

## To do
- identity: id-options ("Which ID can I get?": no national ID card; passport card, PSC, licence, IRP, Age Card
  agecard.ie is "not an identity card", 18+). PSC cost not stated on official pages read -> do not claim.
- citizenship: ISD page says "most within 12 months", Citizens Information says 19 months -> show both.
- welfare.json, health.json, tax.json, housing.json, education.json, work.json, justice.json, local.json.
- Budget 2027 (announced 6 Oct 2026): most weekly payments +€10 from January 2027; pension €309.30; maternity €309;
  fuel €43; minimum wage €14.94 from 1 Jan 2027. Mention as "from January 2027".
- UI: real search over guides + gov.ie directory, guide card, browse by category, life events, deep links #/s/id.
- tools/ie_build.py (inline content into index.html), tools/ie_crawl_govie.py + workflow (robots-respecting crawl of
  https://www.gov.ie/en/services/?page=1..138 -> data/ie/govie-services.json), tools/ie_check_links.py + workflow.
- Banner must stay: unofficial concept, not a government website; guides are summaries, checked date, links official.
- WebFetch only works for URLs that appeared in a WebSearch result: search first, then fetch.
- Publish: repo main + artifact slug 0b73e779-a2cf-44af-8dce-594f660125f1 (get base version first).
