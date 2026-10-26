"""Every message we send, in one place. Plain text with *bold* (WhatsApp style);
channels/telegram.py converts that to Telegram HTML.

Two shapes for each alert-type message: the free text (Telegram, or WhatsApp inside
the 24-hour window) and the parameter list for the matching WhatsApp template
(outside the window). Keep them in sync with the templates in the README.
"""
from __future__ import annotations

from datetime import date

from .matcher import REGION_CHOICES, REGION_KEYS, SECTOR_KEYS, SECTORS, VALUE_BANDS, VALUE_KEYS

CUR = {"EUR": "€", "GBP": "£", "USD": "$"}


def money(value: float | None, currency: str | None) -> str:
    if value is None:
        return "value not stated"
    sym = CUR.get((currency or "EUR").upper(), (currency or "") + " ")
    if value >= 1_000_000:
        n = f"{value / 1_000_000:.1f}".rstrip("0").rstrip(".")
        return f"{sym}{n}m"
    if value >= 1_000:
        return f"{sym}{round(value / 1000)}k"
    return f"{sym}{value:.0f}"


def day(d: date | None) -> str:
    return d.strftime("%a, %-d %b") if d else "deadline not stated"


def days_left(d: date | None, today: date | None = None) -> int | None:
    if d is None:
        return None
    return max(0, (d - (today or date.today())).days)


def one_line(s: str | None, limit: int = 300) -> str:
    """WhatsApp template parameters cannot contain newlines or tabs."""
    s = " ".join((s or "").split())
    return s if len(s) <= limit else s[: limit - 1].rstrip() + "…"


def numbered(keys: list[str], labels: dict[str, str]) -> str:
    return "\n".join(f"{i + 1}. {labels[k]}" for i, k in enumerate(keys))


# --- onboarding ---------------------------------------------------------------

def welcome(name: str | None) -> str:
    hi = f"Hi {name}." if name else "Hi."
    return (f"{hi} I'm *Telpe Tenders*. I read eTenders, Contracts Finder and TED every day and send you "
            f"only the public tenders that fit what you sell.\n\nThree quick questions and you're set.")


def ask_sectors() -> str:
    return ("*What do you sell?* Reply with the numbers, e.g. 2,6\n\n" + numbered(SECTOR_KEYS, SECTORS))


def ask_region() -> str:
    return "*Where do you work?* Reply with one number.\n\n" + numbered(REGION_KEYS, REGION_CHOICES)


def ask_size() -> str:
    return "*What contract size would you bid for?* One number.\n\n" + numbered(VALUE_KEYS, VALUE_BANDS)


def ask_keywords() -> str:
    return ("*Any words that matter in your trade?* e.g. parks, cleaning, website\n"
            "Reply SKIP if not.")


def ask_phone_telegram() -> str:
    return ("Optional: share your phone number with the button below, so your WhatsApp and Telegram "
            "are the same account. Or reply SKIP.")


def done(profile: dict, mode: str) -> str:
    when = "a daily alert around 08:05" if mode == "daily" else "a weekly digest on Monday mornings"
    return (f"Done. You'll get {when}, only when something fits.\n\n"
            f"{profile_text(profile)}\n\n"
            "Reply *MORE* for the next match, *SAVE* to track one, *STOP* to pause, *HELP* for the rest.")


def profile_text(profile: dict) -> str:
    sectors = ", ".join(SECTORS[s] for s in profile.get("sectors") or []) or "any sector"
    region = REGION_CHOICES.get(profile.get("region") or "all", "All of Ireland")
    band = VALUE_BANDS.get(profile.get("band") or "any", "Any size")
    kws = ", ".join(profile.get("keywords") or []) or "none"
    sub = "included" if profile.get("sub", True) else "excluded"
    return (f"*Your profile*\nSectors: {sectors}\nRegion: {region}\nSize: {band}\nKeywords: {kws}\n"
            f"Small (sub-threshold) notices: {sub}")


def first_matches_intro(n: int) -> str:
    if n == 0:
        return "Nothing open fits that profile right now. I'll message you the day something does."
    return f"Here's what fits right now ({n} open). The best one:"


# --- alerts -------------------------------------------------------------------

def alert(t: dict, fit: int, sector: str, today: date | None = None, more: int = 0) -> str:
    dl = days_left(t.get("deadline"), today)
    dl_txt = f" ({dl} days)" if dl is not None else ""
    sub = " · sub-threshold, eTenders only" if t.get("sub") else ""
    summary = t.get("summary") or one_line(t.get("description"), 240)
    tail = f"\n\n_{more} more fit your profile. Reply MORE._" if more else ""
    return (f"*New tender · {t['buyer']}*\n{t['title']}\n\n"
            f"Est. {money(t.get('value'), t.get('currency'))} · closes {day(t.get('deadline'))}{dl_txt}\n"
            f"Fit {fit}% for {sector.lower()}{sub}\n\n"
            f"{summary}\n\n{t['url']}\n\n"
            f"Reply SAVE to track · MORE for the next{tail}")


def alert_params(t: dict, fit: int, sector: str, today: date | None = None) -> list[str]:
    """Parameters for the WhatsApp template `tender_alert` ({{1}}..{{9}}), see README."""
    dl = days_left(t.get("deadline"), today)
    return [
        one_line(t["buyer"], 80),
        one_line(t["title"], 150),
        money(t.get("value"), t.get("currency")),
        day(t.get("deadline")),
        str(dl if dl is not None else "-"),
        str(fit),
        sector.lower() + (" · sub-threshold" if t.get("sub") else ""),
        one_line(t.get("summary") or t.get("description"), 240) or "No description in the notice.",
        one_line(t["url"], 200),
    ]


def digest(items: list[tuple[int, dict]], today: date | None = None) -> str:
    if not items:
        return "*Your week in tenders*\nNothing new fits your profile this week. Nothing to read, nothing missed."
    lines = [f"*Your week in tenders · {len(items)} that fit*", ""]
    for i, (f, t) in enumerate(items, 1):
        lines.append(f"{i}. {t['buyer']} · {t['title']}\n   {money(t.get('value'), t.get('currency'))} · "
                     f"closes {day(t.get('deadline'))} · fit {f}%")
        lines.append("")
    lines.append("Reply a number for the summary and link.")
    return "\n".join(lines)


def digest_params(items: list[tuple[int, dict]], size: int = 4) -> list[str]:
    """Parameters for `tender_digest` ({{1}} count, then {{2}}..{{5}} one line each)."""
    params = [str(len(items))]
    for i in range(size):
        if i < len(items):
            f, t = items[i]
            params.append(one_line(f"{i + 1}. {t['buyer']} · {t['title']} · {money(t.get('value'), t.get('currency'))} · "
                                   f"closes {day(t.get('deadline'))} · fit {f}%", 200))
        else:
            params.append("-")
    return params


def reminder(t: dict, days: int) -> str:
    tip = ("Clarification questions usually close about a week before; check the notice."
           if days > 3 else "Submission is on the portal, not by email. Upload early; portals get slow on deadline afternoons.")
    return (f"*{days} days left · {t['buyer']}*\n{t['title']}\n\nCloses {day(t.get('deadline'))}. {tip}\n\n{t['url']}")


def reminder_params(t: dict, days: int) -> list[str]:
    return [str(days), one_line(t["buyer"], 80), one_line(t["title"], 150), day(t.get("deadline")), one_line(t["url"], 200)]


# --- commands -----------------------------------------------------------------

def saved(t: dict) -> str:
    d = t.get("deadline")
    return (f"Saved. I'll remind you 7 days and 2 days before {day(d)}." if d
            else "Saved. The notice has no deadline I can read, so no reminders for this one.")


def nothing_to_save() -> str:
    return "Nothing to save yet. Reply MORE and I'll show you the next match."


def no_more() -> str:
    return "That's everything that fits right now. I'll message you when something new is published."


def stopped() -> str:
    return "Paused. Reply START whenever you want alerts again."


def resumed() -> str:
    return "Back on. Reply MORE for the latest match."


def mode_set(mode: str) -> str:
    return "Daily alerts it is, around 08:05." if mode == "daily" else "Weekly digest it is, Monday mornings."


def help_text() -> str:
    return ("*Commands*\nMORE – next tender that fits\nSAVE – track the last one (reminders 7 and 2 days before)\n"
            "SAVED – your tracked tenders\nPROFILE – what I match you on\nEDIT – redo your profile\n"
            "DAILY / WEEKLY – how often I write\nSTOP / START – pause and resume\n"
            "DELETE – remove your number and everything I know about you\n\n"
            "Anything else and I'll assume it's a question for a human: cesar@telpe.ai")


def saved_list(items: list[dict], today: date | None = None) -> str:
    if not items:
        return "You haven't saved any tender yet. Reply SAVE after an alert to track it."
    lines = ["*Tracked tenders*"]
    for t in items:
        dl = days_left(t.get("deadline"), today)
        lines.append(f"• {t['buyer']} · {t['title']} · closes {day(t.get('deadline'))}" + (f" ({dl} days)" if dl is not None else ""))
    return "\n".join(lines)


def not_understood() -> str:
    return "Sorry, I didn't get that. Reply HELP to see what I understand."


def invalid_choice() -> str:
    return "Please reply with the number(s) from the list."


def telegram_linked(phone: str) -> str:
    return f"Thanks, linked to {phone}. Alerts will come here on Telegram."


def deleted() -> str:
    return "Done. Your number, profile, alerts and this conversation are deleted. Write JOIN if you ever want back in."
