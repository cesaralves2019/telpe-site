from datetime import timedelta

from app import conversation, db, jobs
from app.channels import Inbound, router


def tg(text, chat="42", phone=None, name="Ana"):
    conversation.handle(Inbound(channel="telegram", external_id=chat, text=text, name=name, phone=phone))


def wa(text, wa_id="353851234567", name="Ana"):
    conversation.handle(Inbound(channel="whatsapp", external_id=wa_id, text=text, name=name, phone=wa_id))


def onboard_telegram(outbox, chat="42"):
    tg("/start", chat)
    tg("2,6", chat)
    tg("2", chat)   # Dublin
    tg("5", chat)   # any size
    tg("SKIP", chat)
    tg("SKIP", chat)


def test_telegram_onboarding_end_to_end(outbox):
    jobs.seed_sample()
    tg("/start")
    assert "Telpe Tenders" in outbox.texts()[0] and "What do you sell" in outbox.texts()[1]
    tg("2,6")
    assert "Where do you work" in outbox.texts()[-1]
    tg("2")
    assert "contract size" in outbox.texts()[-1]
    tg("5")
    assert "words that matter" in outbox.texts()[-1]
    tg("SKIP")
    assert "share your phone" in outbox.texts()[-1].lower() and outbox.last()["keyboard"]["keyboard"][0][0]["request_contact"]
    tg("SKIP")
    user = db.users().find_one({"telegram.chat_id": "42"})
    assert user["status"] == "active" and user["profile"] == {"sectors": ["cleaning", "landscaping"], "region": "dublin", "band": "any", "keywords": [], "sub": True}
    texts = outbox.texts()
    assert any("Done." in t for t in texts) and any("New tender ·" in t for t in texts)
    first = next(t for t in texts if "New tender ·" in t)
    assert "Dublin City Council" in first or "HSE" in first  # Dublin profile: a Dublin or national buyer
    assert db.alerts().count_documents({"user_id": user["_id"]}) == 1
    assert user["last_tender_id"] is not None


def test_commands_after_onboarding(outbox):
    jobs.seed_sample()
    onboard_telegram(outbox)
    outbox.clear()
    tg("MORE")
    assert "New tender ·" in outbox.last()["text"]
    assert db.alerts().count_documents({}) == 2
    tg("SAVE")
    assert "Saved." in outbox.last()["text"]
    assert db.alerts().count_documents({"saved": True}) == 1
    tg("SAVED")
    assert "Tracked tenders" in outbox.last()["text"]
    tg("PROFILE")
    assert "Your profile" in outbox.last()["text"]
    tg("WEEKLY")
    assert db.users().find_one({"telegram.chat_id": "42"})["mode"] == "weekly"
    tg("STOP")
    assert db.users().find_one({"telegram.chat_id": "42"})["status"] == "paused"
    tg("START")
    assert db.users().find_one({"telegram.chat_id": "42"})["status"] == "active"
    tg("blah")
    assert "didn't get that" in outbox.last()["text"]
    tg("HELP")
    assert "Commands" in outbox.last()["text"]


def test_more_until_exhausted(outbox):
    jobs.seed_sample()
    onboard_telegram(outbox)
    for _ in range(10):
        tg("MORE")
    assert "everything that fits" in outbox.last()["text"]


def test_whatsapp_onboarding_and_window(outbox):
    jobs.seed_sample()
    wa("JOIN")
    assert outbox.last()["channel"] == "whatsapp" and outbox.last()["template"] is None
    wa("1")       # construction
    wa("1")       # all of Ireland
    wa("5")       # any size
    wa("playground, stonework")
    user = db.users().find_one({"whatsapp.wa_id": "353851234567"})
    assert user["status"] == "active" and user["phone"] == "353851234567"
    assert user["profile"]["keywords"] == ["playground", "stonework"]
    assert any("Fingal" in t or "Office of Public Works" in t for t in outbox.texts())  # keyword hits rank first
    assert db.alerts().count_documents({"user_id": user["_id"]}) == 1

    # Window closed → alerts go out as templates with single-line parameters
    db.users().update_one({"_id": user["_id"]}, {"$set": {"whatsapp.last_inbound_at": db.now() - timedelta(hours=30)}})
    user = db.users().find_one({"_id": user["_id"]})
    outbox.clear()
    conversation.send_next_match(user)
    sent = outbox.last()
    assert sent["template"] == "tender_alert" and len(sent["params"]) == 9
    assert all("\n" not in p for p in sent["params"])

    # Window closed and no template → skipped, logged, nothing crashes
    entry = router.deliver(user, "hello")
    assert entry["status"] == "skipped"


def test_telegram_contact_links_whatsapp_account(outbox):
    jobs.seed_sample()
    wa("JOIN"); wa("2"); wa("1"); wa("5"); wa("SKIP")
    assert db.users().count_documents({}) == 1
    tg("/start", chat="77")
    assert db.users().count_documents({}) == 2
    conversation.handle(Inbound(channel="telegram", external_id="77", text="", name="Ana", phone="353851234567"))
    assert db.users().count_documents({}) == 1
    user = db.users().find_one({"phone": "353851234567"})
    assert user["telegram"]["chat_id"] == "77" and user["whatsapp"]["wa_id"] == "353851234567"
    assert user["status"] == "active" and user["profile"]["sectors"] == ["cleaning"]
    assert router.preferred_channel(user) == "telegram"
    outbox.clear()
    router.deliver(user, "ping")
    assert outbox.last()["channel"] == "telegram"


def test_edit_restarts_profile(outbox):
    jobs.seed_sample()
    onboard_telegram(outbox)
    tg("EDIT")
    assert "What do you sell" in outbox.last()["text"]
    tg("3")
    tg("2")
    tg("5")
    tg("SKIP")  # phone is not asked a second time
    user = db.users().find_one({"telegram.chat_id": "42"})
    assert user["profile"]["sectors"] == ["it"] and user["status"] == "active"


def test_delete_removes_everything(outbox):
    jobs.seed_sample()
    onboard_telegram(outbox)
    tg("SAVE")
    assert db.users().count_documents({}) == 1 and db.alerts().count_documents({}) == 1
    tg("DELETE")
    assert "deleted" in outbox.last()["text"]
    assert db.users().count_documents({}) == 0 and db.alerts().count_documents({}) == 0 and db.messages().count_documents({}) == 0
