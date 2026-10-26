# Telpe Tenders — backend

WhatsApp and Telegram alerts for public tenders in Ireland and the UK. This is the
service behind the mock-up at [telpe.ai](https://telpe.ai): it reads eTenders,
Contracts Finder and TED, matches notices to what a supplier sells, and sends one
message a day (or a Monday digest) on the channel the person has.

**Rule for channels:** if the person has Telegram, they get Telegram. Otherwise WhatsApp.
(Telegram is free and has no template rules; WhatsApp costs about €0.014 per alert.)

```
                 ┌────────────┐   ┌──────────────────┐   ┌───────────┐
 sources ──────▶ │  tenders   │──▶│ matcher (fit %)  │──▶│  router   │──▶ Telegram Bot API
 TED, CF,        │  (MongoDB) │   │ per user profile │   │           │──▶ WhatsApp Cloud API
 eTenders        └────────────┘   └──────────────────┘   └───────────┘
                        ▲                                        │
                        │        webhooks (FastAPI) ◀────────────┘  replies: SAVE · MORE · STOP …
```

Everything is plain Python, one process for the webhooks and one for the timetable.

## 1. Quick start (15 minutes, Telegram only, sample data)

You need Python 3.11+ and a MongoDB (Atlas free tier or Docker, see §2).

```bash
git clone <this repo> && cd telpe-tenders
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # fill MONGODB_URI and TELEGRAM_BOT_TOKEN (see §2 and §3)

python -m app.jobs seed-sample  # 18 illustrative notices so there is something to match
python -m app.poll_telegram     # no public URL needed; prints the bot link
```

Open the bot in Telegram, send `/start`, answer the three questions. You should get
"Done." and the best matching notice straight away. Then try `MORE`, `SAVE`, `SAVED`,
`PROFILE`, `WEEKLY`, `STOP`, `HELP`.

Run the test suite any time: `pip install pytest mongomock && pytest`.

## 2. MongoDB

**Atlas (free, hosted):**
1. [cloud.mongodb.com](https://cloud.mongodb.com) → create a project → *Build a Database* → **M0 Free** → region Ireland (eu-west-1).
2. *Database Access* → add a database user with a password (role: read and write to any database).
3. *Network Access* → add IP → for testing, `0.0.0.0/0` (anywhere); narrow it later to your server's IP.
4. *Connect* → *Drivers* → copy the string, put the password in, set it as `MONGODB_URI`:
   `mongodb+srv://USER:PASSWORD@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`

**Local (Docker):** `docker compose up mongo` and keep `MONGODB_URI=mongodb://localhost:27017`.

Collections and indexes are created automatically on first run (`app/db.py`).

### Data model

| collection | one document per | key fields |
|---|---|---|
| `users` | person | `phone` (digits, unique), `name`, `telegram{chat_id}`, `whatsapp{wa_id,last_inbound_at}`, `profile{sectors[],region,band,keywords[],sub}`, `state` (onboarding step or `active`), `status` (`onboarding`/`active`/`paused`), `mode` (`daily`/`weekly`), `last_tender_id`, `last_digest[]` |
| `tenders` | notice | `_id = source:source_id`, `source`, `title`, `description`, `summary`, `buyer`, `cpv[]`, `country`, `nuts[]`, `value`, `currency`, `published_at`, `deadline`, `url`, derived `sectors[]`, `region`, `band`, `sub` |
| `alerts` | (user, tender) shown | `fit`, `kind` (welcome/alert/more/digest), `sent_at`, `saved`, `reminders_sent[]` |
| `messages` | message in or out | `direction`, `channel`, `user_id`, `text`, `template`, `status` (sent/failed/skipped), `error`, `at` |
| `jobs` | scheduled job | `ran_at`, last report |

A person who joins on WhatsApp and later on Telegram is merged by phone number
(Telegram asks once, with a "Share my number" button; it's optional).

## 3. Telegram

1. In Telegram, open **@BotFather** → `/newbot` → pick a name and a username ending in `bot`.
2. Copy the token into `TELEGRAM_BOT_TOKEN`; put the username (without @) in `TELEGRAM_BOT_USERNAME`.
3. Optional but recommended: `/setdescription`, `/setabouttext`, `/setuserpic` in BotFather.
4. **Development:** `python -m app.poll_telegram` (long polling, deletes any webhook first).
5. **Production:** run the web app (§6) on a public HTTPS URL, set a random
   `TELEGRAM_WEBHOOK_SECRET`, then once:
   `python -m app.channels.telegram set-webhook https://YOUR-HOST/webhooks/telegram`

Join link for the website: `https://t.me/<bot username>`.

## 4. WhatsApp (Meta Cloud API, no Twilio)

### 4.1 Create the app and get a free test number
1. [developers.facebook.com](https://developers.facebook.com) → *My Apps* → **Create app** → type **Business**.
   You'll be asked for (or guided to create) a *Meta Business Account*; the company is Telpe AI.
2. In the app dashboard → *Add product* → **WhatsApp** → *Set up*. This creates a **test WhatsApp
   Business Account** and a **test phone number**. Messages from the test number are free.
3. *WhatsApp → API Setup*:
   - copy **Phone number ID** → `WHATSAPP_PHONE_NUMBER_ID` (it's an ID, not the phone number);
   - copy the **temporary access token** → `WHATSAPP_TOKEN` (valid 24 h; for a permanent one see 4.4);
   - under *To*, **Manage phone number list** → add the phones that may receive messages
     (your own, then friends: **up to 5**; each gets a code on WhatsApp to confirm).
   - put the test number's digits (e.g. `15551234567`) in `WHATSAPP_DISPLAY_NUMBER` (for the wa.me link).
4. Still in API Setup, click **Send message** (template `hello_world`). If it arrives, the account works.
   From the terminal the same check is `python -m app.channels.whatsapp hello 353851234567`.

### 4.2 Webhook (so people can write to the bot)
1. Run the web app locally: `uvicorn app.main:app --port 8000`, and expose it:
   `ngrok http 8000` (or `cloudflared tunnel --url http://localhost:8000`). Copy the https URL.
2. App dashboard → *WhatsApp → Configuration* → **Webhook** → *Edit*:
   - Callback URL: `https://YOUR-NGROK-URL/webhooks/whatsapp`
   - Verify token: the value of `WHATSAPP_VERIFY_TOKEN` in your `.env` (any string you chose).
   Meta calls `GET /webhooks/whatsapp` once; the app answers the challenge and Meta saves it.
3. Under *Webhook fields* → **Subscribe** to `messages`.
4. *App settings → Basic* → copy **App secret** → `WHATSAPP_APP_SECRET`. The app uses it to check
   the `X-Hub-Signature-256` header, so only Meta can post to the webhook.
5. From one of the 5 test phones, write **JOIN** to the test number. The onboarding should start.

Replies inside the 24-hour window after the person's last message are free-form and free.

### 4.3 Templates (needed for the daily alert, digest and reminders)
Outside the 24-hour window the API only accepts **approved templates**. Create these three in
**WhatsApp Manager → Message templates → Create template**, category **Utility**, language English,
names exactly as in `.env` (`tender_alert`, `tender_digest`, `deadline_reminder`). Meta asks for a
sample value per variable; use anything realistic. Approval is usually minutes to a few hours.

`tender_alert` — body (9 variables, matches `text.alert_params`):
```
New tender · {{1}}
{{2}}

Est. {{3}} · closes {{4}} ({{5}} days)
Fit {{6}}% for {{7}}

{{8}}

{{9}}

Reply SAVE to track · MORE for the next · STOP to pause
```

`tender_digest` — body (5 variables, matches `text.digest_params`):
```
Your week in tenders · {{1}} that fit

{{2}}

{{3}}

{{4}}

{{5}}

Reply a number for the summary and link, or STOP to pause.
```

`deadline_reminder` — body (5 variables, matches `text.reminder_params`):
```
{{1}} days left · {{2}}
{{3}}

Closes {{4}}. Submission is on the portal, not by email; upload early.

{{5}}
```

Notes: variables cannot contain line breaks (the code flattens them); Meta can re-categorise a
template as Marketing (≈3.5× the price) if it reads as promotional, so keep the wording factual;
a template that isn't approved yet makes the send fail with a clear error in `messages.error`.

### 4.4 Going live
- **Permanent token:** Business Settings → *Users → System users* → add a system user (admin) →
  *Generate token* for the app with `whatsapp_business_messaging` and `whatsapp_business_management`
  → `WHATSAPP_TOKEN`. (The temporary token from API Setup dies after 24 h.)
- **Real number:** *API Setup → Add phone number* (a number not yet on WhatsApp; a prepaid SIM is fine),
  verify it, and complete **Business verification** in Business Settings to lift the test limits.
- **Display name** must match the business; **opt-in** is required by Meta's policy — the JOIN
  message and the website buttons count, keep the `messages` log as the record.

### 4.5 What it costs (Meta rate card, October 2026)
Per *delivered* message, by the recipient's country. Ireland is in "Rest of Western Europe":
utility ≈ **€0.0142**, marketing ≈ €0.049; UK utility ≈ $0.022. Free-form replies inside the
24-hour window: 1,000 free per number per month, then the utility rate. Inbound is free.
A Pro user getting 1 alert a day plus a few reminders ≈ €0.45–0.60/month. Telegram: €0.

## 5. Sources

| source | how | notes |
|---|---|---|
| **eTenders** (IE) | reads the public *Latest CfTs* table, newest first | no API/RSS; title, buyer, dates, value, link; CPV only on the detail page (`fetch_detail`). Be polite: 1 request/s, a few pages/day. History since 2013: [OGP open dataset](https://data.gov.ie/dataset/contract-notices-published-on-etenders) (CSV, CC BY). |
| **TED** (EU) | Search API v3, no key | Irish notices land here 1–3 days after eTenders; UK above-threshold too. Fair use 700 req/min. |
| **Contracts Finder** (UK) | OCDS search API, no key | England/Wales/NI incl. sub-threshold. 403 = rate limit, wait 5 min. |

Not yet wired: Find a Tender (UK above-threshold, OCDS API), Public Contracts Scotland, eSourcing NI.

```bash
python -m app.jobs fetch              # all sources, last 2 days
python -m app.jobs fetch etenders     # one source
python -m app.jobs stats
```

Summaries: with `ANTHROPIC_API_KEY` set, each new notice with a description gets a three-sentence
summary (Claude Haiku, ~€0.001 each). Without it, the alert shows the first 240 characters.

## 6. Running it for real

Two processes:
- **web**: `uvicorn app.main:app --host 0.0.0.0 --port 8000` — the webhooks, `/health`, `/links`.
- **scheduler**: `python -m app.scheduler` — fetch hourly, daily alerts at 08:05, digest Monday
  08:00, reminders at 09:00 (Europe/Dublin; all in `.env`). Remembers last runs in `jobs`, so a
  restart never double-sends. (If you prefer cron: `python -m app.jobs all` once a day works too.)

`docker compose up --build` runs Mongo + web + scheduler locally. For hosting, any container host
with a public HTTPS URL does (Railway, Render, Fly.io: ~€5/month): deploy the Dockerfile twice with
the two commands above, set the env vars, point Meta and Telegram at `https://host/webhooks/...`.

## 7. Wiring the website

`GET /links` returns `{"telegram": "https://t.me/<bot>", "whatsapp": "https://wa.me/<number>?text=JOIN"}`.
Replace the "Start free" modal on telpe.ai with those two buttons: the person opens the chat
themselves, which is also the opt-in WhatsApp requires. No form, no number typed into a website.

## 8. Known limits / next

- eTenders list parsing will break when their HTML changes; `tests/test_sources.py` has the fixture.
- Region is guessed from the buyer's name (county → province); national bodies count as "Ireland".
- Sub-threshold is a heuristic (eTenders notices under €221k).
- No payments, no plans: `plan` isn't enforced yet — everyone gets the Pro behaviour.
- GDPR: phone numbers and chat logs are personal data. `DELETE` wipes a person completely; still add
  a retention rule for `messages` (e.g. 90 days) and a privacy note before inviting strangers.
