"""Text for GHL contact notes and tasks (kept separate so it is easy to edit)."""
import datetime
from zoneinfo import ZoneInfo

WHY = ("OnCall Local places a short automated call after business hours to local service companies to check whether "
       "their phone is answered after hours. A missed after-hours call is usually a lost job. If nobody answers, we follow up "
       "with an email and a call about Missed Call Text Back: every missed caller gets an instant text, an AI assistant "
       "collects the job details, and the owner gets the conversation to call back.")

PITCH = ("Missed Call Text Back: instant text to every missed caller, AI collects what they need, you get the full conversation "
         "to call back. $247 setup + $247/mo, no contract, cancel anytime.")

NEXT = {
    "answered": "No action. Someone answers after hours, so this is not a prospect for now.",
    "attempt1": "Retry on the next calling evening. Two misses on different evenings = prospect.",
    "prospect": "PROSPECT: call during business hours (see the task) and send the follow-up email the next morning.",
}

def stamp(tz, when=None):
    when = (when or datetime.datetime.now(ZoneInfo(tz))).astimezone(ZoneInfo(tz))
    return when.strftime("%a %b %-d, %Y %-I:%M %p %Z")

def business_block(c, fields):
    """c: GHL contact dict; fields: {name: value} of our custom fields."""
    addr = ", ".join(x for x in (c.get("address1"), c.get("city"), c.get("state")) if x)
    tags = [t.lower() for t in c.get("tags", [])]
    line = next((t.replace("mce-line-", "") for t in tags if t.startswith("mce-line-")), "unknown")
    rows = [("Business", c.get("companyName") or c.get("contactName")), ("Phone", f"{c.get('phone')} ({line})"),
            ("Website", c.get("website")), ("Email", c.get("email") or "none found"), ("Address", addr),
            ("Google", f"{fields.get('rating','?')} stars, {fields.get('reviews','?')} reviews"),
            ("Trade", fields.get("trade")), ("Listed 24/7", "yes" if "mce-24-7" in tags else "no"), ("Owner (confirm when you call)", fields.get("owner"))]
    return "\n".join(f"{k}: {v}" for k, v in rows if v)

def call_note(c, fields, result, attempt, call, message, tz, prospect, misses_needed=2):
    status = (call or {}).get("status"); by = (call or {}).get("answered_by") or "n/a"
    detail = f"Twilio status {status}, detected {by}, {(call or {}).get('duration','0')}s, call {(call or {}).get('sid','n/a')}"
    nxt = NEXT["answered"] if result == "answered" else NEXT["prospect"] if prospect else NEXT["attempt1"]
    played = ("Message played to a live answer." if result == "answered" else
              "Hung up on the voicemail; no message was left." if result == "voicemail" else "No one picked up; no message delivered.")
    return (f"MCTB PROSPECTING CALL | {stamp(tz)}\n"
            f"Disposition: {result.upper()}" + (f" (attempt {attempt} of {misses_needed})" if misses_needed > 1 else "") + "\n\n"
            f"Why we called: {WHY}\n\nMessage: \"{message}\"\n{played}\n\nResult detail: {detail}\n\n"
            f"{business_block(c, fields)}\n\nNext step: {nxt}")

def prospect_task(c, fields, history, tz):
    """history: list of 'Wednesday 7:12 PM: voicemail' strings (oldest first)."""
    name = c.get("companyName") or c.get("contactName")
    once = len(history) == 1
    head = ("They did not answer our after-hours call." if once else "They did not answer our after-hours call on two evenings.")
    when = "last night" if once else "twice this week"
    return (f"CALL THIS PROSPECT. {head}\n\n{business_block(c, fields)}\n\n"
            f"Call history:\n" + "\n".join(f"- {h}" for h in history) + f"\n\nWhy we called: {WHY}\n\n"
            f"Suggested opener: \"Hi, this is Sam with OnCall Local. We called {name} after hours {when} to see how your phones are covered, and nobody picked up. "
            f"When a customer calls with an emergency after hours, what happens to that call?\"\n\n"
            f"Offer: {PITCH}\n\nAfter the call: set the opportunity stage in Missed Call Prospects and add a note with what they said.")

def manual_task(c, fields):
    return (f"MANUAL CALL: this number is a mobile phone, so it is never auto-dialed.\n\n{business_block(c, fields)}\n\n"
            f"Why on your list: {WHY}\n\nSuggested opener: \"Hi, this is Sam with OnCall Local. Quick question: when a customer "
            f"calls {c.get('companyName') or 'your company'} after hours and you can't pick up, what happens to that call?\"\n\nOffer: {PITCH}")
