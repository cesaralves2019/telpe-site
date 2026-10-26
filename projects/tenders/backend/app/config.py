"""Configuration. Everything comes from environment variables (or a .env file).

Copy .env.example to .env and fill in what you have. Nothing here is required to
*import* the app; each feature checks for its own settings when it is used.
"""
import os

from dotenv import load_dotenv

load_dotenv()


def env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value not in (None, "") else default


# --- database -----------------------------------------------------------------
# MongoDB Atlas looks like: mongodb+srv://USER:PASSWORD@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
# Local docker:            mongodb://localhost:27017
# Tests:                   mongomock://
MONGODB_URI = env("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = env("MONGODB_DB", "telpe_tenders")

# --- Telegram -----------------------------------------------------------------
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN")
# Any random string. Sent by Telegram in the X-Telegram-Bot-Api-Secret-Token header
# so nobody else can post fake updates to the webhook.
TELEGRAM_WEBHOOK_SECRET = env("TELEGRAM_WEBHOOK_SECRET")
TELEGRAM_BOT_USERNAME = env("TELEGRAM_BOT_USERNAME")  # without @, used in links

# --- WhatsApp (Meta Cloud API) ------------------------------------------------
WHATSAPP_TOKEN = env("WHATSAPP_TOKEN")                      # access token (temporary 24h one, or a System User token)
WHATSAPP_PHONE_NUMBER_ID = env("WHATSAPP_PHONE_NUMBER_ID")  # "Phone number ID" from API Setup, not the phone number
WHATSAPP_DISPLAY_NUMBER = env("WHATSAPP_DISPLAY_NUMBER")    # the number people write to, for wa.me links (digits only)
WHATSAPP_VERIFY_TOKEN = env("WHATSAPP_VERIFY_TOKEN", "telpe-verify")  # you choose it; paste the same in Meta's webhook config
WHATSAPP_APP_SECRET = env("WHATSAPP_APP_SECRET")            # App settings > Basic > App secret; verifies webhook signatures
GRAPH_API_VERSION = env("GRAPH_API_VERSION", "v23.0")
# Template names as approved in WhatsApp Manager (see README, "WhatsApp templates").
WHATSAPP_TEMPLATE_ALERT = env("WHATSAPP_TEMPLATE_ALERT", "tender_alert")
WHATSAPP_TEMPLATE_DIGEST = env("WHATSAPP_TEMPLATE_DIGEST", "tender_digest")
WHATSAPP_TEMPLATE_REMINDER = env("WHATSAPP_TEMPLATE_REMINDER", "deadline_reminder")
WHATSAPP_TEMPLATE_LANG = env("WHATSAPP_TEMPLATE_LANG", "en")

# --- summaries (optional) -----------------------------------------------------
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
SUMMARY_MODEL = env("SUMMARY_MODEL", "claude-haiku-4-5-20251001")

# --- schedule -----------------------------------------------------------------
TIMEZONE = env("TIMEZONE", "Europe/Dublin")
DAILY_SEND_AT = env("DAILY_SEND_AT", "08:05")      # HH:MM local time
WEEKLY_SEND_AT = env("WEEKLY_SEND_AT", "08:00")    # Mondays
REMINDERS_AT = env("REMINDERS_AT", "09:00")
FETCH_EVERY_MINUTES = int(env("FETCH_EVERY_MINUTES", "60"))

# --- matching defaults ----------------------------------------------------------
MIN_FIT = int(env("MIN_FIT", "70"))      # below this we don't send
DAILY_LIMIT = int(env("DAILY_LIMIT", "1"))  # alerts per day per user; "MORE" gives the next one
DIGEST_SIZE = int(env("DIGEST_SIZE", "4"))
