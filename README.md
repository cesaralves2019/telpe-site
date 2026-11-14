# telpe.ai

Static site, deployed from `main`.

## The root page: Ireland.gov concept

`index.html` is an unofficial concept by Telpe AI: one question box in front of Ireland's public services, in the
manner of America.gov. It is **not a government website** and says so in a band that never leaves the screen.
Since 14 November 2026 it carries real content: 74 plain-language guides (passports, driving licence, PPS number,
immigration, benefits, health, tax, housing, work, and so on). Each guide says who it is for, what you need, the
steps, cost and time, the usual "in my case" situations, and lists the official pages it was read from.
Every button opens the official service in a new tab; nothing is submitted on the page.

| Path | What it is |
| --- | --- |
| `content/ie/*.json` | The guides, one file per topic. Only facts read on an official page on the checked date; each guide lists those pages in `src`. `content/ie/NOTES.md` has the content model and working notes. |
| `content/ie/sets/life-events.json` | "What is happening" sets (moved to Ireland, having a baby, lost my job, ...). |
| `tools/ie_build.py` | Validates the guides (ids, internal links, https) and writes them into `index.html`. Run it after editing content: `python3 tools/ie_build.py`. |
| `tools/ie_check_links.py` | One request per link used in the guides; skips sites whose robots.txt disallows or refuses automated readers. Runs on GitHub (`.github/workflows/ie-data.yml`) and commits `data/ie/links-report.json`. |

Sources are Irish public bodies (gov.ie, Citizens Information, DFA, HSE, Revenue, NDLS/RSA, Immigration Service
Delivery, RTB, An Garda Síochána); their content is re-usable under CC BY 4.0 with attribution, which the page
gives. gov.ie refuses automated readers (HTTP 403), so its catalogue of about 1,400 service pages is not copied:
the search links to gov.ie's own listing instead.

## Earlier pages kept in this repo

| Folder | What it is | Live at |
| --- | --- | --- |
| `company.html`, `studio.html`, `game.html` | The original Telpe AI page (headline and the isometric massing model) and its two companions. | `/company.html` |
| `projects/apuracao-2026/` | 2026 Brazilian runoff results tracker on official TSE data (race card, state map, march-of-the-count chart, projection + Monte Carlo, chatbot, PT/EN/ES). `standalone.html` is the single-file copy; `tools/mock/` is the fake TSE mirror used to test it. | `/projects/apuracao-2026/` |
| `projects/tenders/` | Telpe Tenders: landing, `how.html`, `try.html`, `pricing.html`, and the Python service in `backend/`. | `/projects/tenders/` |

Data and automation for the tracker stay at the root so the GitHub Actions keep working: `data/r1-march.json`,
`data/series.json`, `data/live/`, `data/r1/`, `tools/build_r1_march.py`, `tools/record_series.py`,
`tools/eval_projection.py`.
