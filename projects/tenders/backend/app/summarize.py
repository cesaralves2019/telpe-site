"""Three-line plain-English summary of a notice, with Claude. Optional: without
ANTHROPIC_API_KEY the alert shows the first 240 characters of the description instead."""
from __future__ import annotations

from . import config

PROMPT = """You write one-paragraph summaries of public tender notices for small suppliers who have 30 seconds.
In at most three short sentences say: what the buyer is purchasing (and for how long, if stated),
anything a supplier must have to qualify (certifications, insurance, references, licences), and
any date or site visit worth knowing. Plain English, no preamble, no bullet points, no quotes.
If the text is too thin to say anything useful, reply with the single word NONE.

Buyer: {buyer}
Title: {title}
Notice text:
{description}"""


def summarize(tender: dict) -> str | None:
    if not config.ANTHROPIC_API_KEY or not tender.get("description"):
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model=config.SUMMARY_MODEL, max_tokens=220,
            messages=[{"role": "user", "content": PROMPT.format(buyer=tender.get("buyer", ""), title=tender.get("title", ""),
                                                                description=(tender.get("description") or "")[:6000])}])
        out = " ".join(block.text for block in msg.content if getattr(block, "type", "") == "text").strip()
        return None if not out or out.upper() == "NONE" else out
    except Exception as e:  # never let a summary failure block an alert
        print(f"summary failed for {tender.get('_id')}: {e}")
        return None
