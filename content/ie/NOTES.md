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

## State on 14 Nov 2026 (first release)
74 guides in 13 topic files, all wired into index.html by tools/ie_build.py; 10 life-event sets.
Search, guide view, topic and life-event lists, deep links (#/s/id, #/c/topic, #/l/set, #/q/words) tested in a
browser on desktop and phone widths.
Link check (GitHub Action): 241 links; 97 answered 200; 139 sit on sites that refuse automated readers (gov.ie,
citizensinformation.ie, ireland.ie, ndls.ie ...), of which the source pages were all opened and read on the day.
gov.ie returns 403 to automated readers, so its full catalogue was NOT copied (owner's rule); the search falls
back to a link to https://www.gov.ie/en/services/.

## Ideas for the next pass
- More guides: SEAI home energy grants, Local Authority Home Loan, CAO, school transport, small claims, planning
  permission, auto-enrolment (My Future Fund), bereavement payments, maternity care scheme, international protection.
- Budget 2027 rates start in January 2027: update welfare.json (rates already mentioned as "from January 2027").
- Citizenship processing time: ISD says 12 months, Citizens Information 19 months (both shown).
- PSC cost is not stated on the official pages read, so no claim is made.
- WebFetch only reads URLs that appeared in a WebSearch result: search first, then fetch.
- Artifact: slug 0b73e779-a2cf-44af-8dce-594f660125f1 (get the live version before publishing).
