# telpe.ai

Static site, deployed from `main`. The root is the original Telpe AI page (one screen: headline and the
isometric massing model), with `studio.html` and `game.html` beside it.

## Projects kept in this repo

Everything built on the site since then lives under `projects/`, untouched and still working at its own path:

| Folder | What it is | Live at |
| --- | --- | --- |
| `projects/apuracao-2026/` | 2026 runoff results tracker on official TSE data: race card, state map, minute-by-minute log, Curitiba/Caibi spotlights, exterior by country, governors, march-of-the-count chart, benchmarked projection + Monte Carlo, Portuguese chatbot, PT/EN/ES switch. `standalone.html` is the single-file copy with the first-round march and the night's series embedded. `tools/mock/` is the fake TSE mirror used to test it (`python3 mock_tse.py live`, then `serve.py`, then open the page with `?src=http://127.0.0.1:8765/oficial`). | `/projects/apuracao-2026/` |
| `projects/tenders/` | Telpe Tenders: the one-screen landing (`index.html`), `how.html`, `try.html`, `pricing.html`, and in `backend/` the Python service (FastAPI + MongoDB, Telegram and WhatsApp bots, matcher, tests). | `/projects/tenders/` |

Data and automation for the tracker stay at the root so the GitHub Actions keep working:

- `data/r1-march.json` — the first round's count minute by minute, rebuilt from the TSE ballot-box bulletins by `tools/build_r1_march.py` (`.github/workflows/r1-march.yml`).
- `data/series.json`, `data/live/`, `data/r1/` — election-night recordings by `tools/record_series.py` (`.github/workflows/marcha.yml`, `marcha-loop.yml`).
- `tools/eval_projection.py` — runs the tracker's projection offline on those files.
