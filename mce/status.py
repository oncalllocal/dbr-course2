"""System status snapshot (read-only): GHL counts, today's Twilio calls, credit balances. Prints JSON."""
import os, json, datetime, requests
from collections import Counter
from zoneinfo import ZoneInfo
from . import ghl
from .config import *

def twilio_today(tz="America/New_York"):
    sid, tok = os.environ.get("TWILIO_ACCOUNT_SID"), os.environ.get("TWILIO_AUTH_TOKEN")
    if not sid: return {}
    start = datetime.datetime.now(ZoneInfo(tz)).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(datetime.timezone.utc)
    base = f"https://api.twilio.com/2010-04-01/Accounts/{sid}"
    calls, url = [], base + "/Calls.json"; params = {"StartTime>": start.strftime("%Y-%m-%d"), "PageSize": 200}
    while url:
        j = requests.get(url, params=params, auth=(sid, tok), timeout=30).json(); calls += j.get("calls", [])
        url = ("https://api.twilio.com" + j["next_page_uri"]) if j.get("next_page_uri") else None; params = None
    bal = requests.get(base + "/Balance.json", auth=(sid, tok), timeout=30).json()
    return {"calls_today": len(calls), "by_status": dict(Counter(c["status"] for c in calls)),
            "by_answered_by": dict(Counter((c.get("answered_by") or "n/a") for c in calls)), "balance": bal.get("balance"), "currency": bal.get("currency")}

def bee_usage():
    k = os.environ.get("SCRAPINGBEE_API_KEY")
    if not k: return {}
    j = requests.get("https://app.scrapingbee.com/api/v1/usage", params={"api_key": k}, timeout=30).json()
    return {"used": j.get("used_api_credit"), "max": j.get("max_api_credit"), "renews": (j.get("renewal_subscription_date") or "")[:10]}

def snapshot():
    cs = ghl.list_contacts(None)
    tags = lambda c: {t.lower() for t in c.get("tags", [])}
    ids = ghl.field_ids(); rev = {v: k for k, v in ids.items() if v}
    rows = []
    for c in cs:
        t = tags(c)
        if "mce-prospect" not in t: continue
        f = {rev[x["id"]]: x.get("value") for x in c.get("customFields", []) if x.get("id") in rev}
        rows.append({"name": c.get("companyName") or c.get("contactName"), "tags": t, "score": float(f.get("score") or 0), "trade": f.get("trade") or "", "outcome": f.get("outcome"),
                     "reviews": f.get("reviews"), "rating": f.get("rating"), "email": bool(c.get("email"))})
    cnt = lambda tag: sum(tag in r["tags"] for r in rows)
    today = f"mce-called-{datetime.datetime.now(ZoneInfo('America/New_York')):%Y%m%d}"
    called_today = [r for r in rows if today in r["tags"]]
    pause = [c for c in cs if "mce-pause" in tags(c)]
    return {"generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "paused": bool(pause),
            "pool": {"imported": len(rows), "queued": cnt(TAG_QUEUE), "answered": cnt(TAG_ANSWERED), "no_answer_prospects": cnt(TAG_NOANSWER),
                     "attempt_1": cnt("mce-attempt-1"), "voicemail": cnt("mce-voicemail"), "ringout": cnt("mce-ringout"),
                     "manual_cells": cnt(TAG_CELL_MANUAL), "manual_tasked": cnt(TAG_MANUAL_TASKED), "with_email": sum(r["email"] for r in rows), "listed_24_7": cnt(TAG_24_7)},
            "last_run": {"called": len(called_today), "answered": sum(TAG_ANSWERED in r["tags"] for r in called_today),
                         "voicemail": sum("mce-voicemail" in r["tags"] for r in called_today), "ringout": sum("mce-ringout" in r["tags"] for r in called_today)},
            "by_trade": [{"trade": k, "leads": v, "queued": sum(TAG_QUEUE in r["tags"] for r in rows if r["trade"] == k), "answered": sum(TAG_ANSWERED in r["tags"] for r in rows if r["trade"] == k),
                          "prospects": sum(TAG_NOANSWER in r["tags"] for r in rows if r["trade"] == k)} for k, v in Counter(r["trade"] for r in rows).most_common()],
            "score_tiers": {"70+": sum(r["score"] >= 70 for r in rows), "50-69": sum(50 <= r["score"] < 70 for r in rows), "25-49": sum(25 <= r["score"] < 50 for r in rows)},
            "twilio": twilio_today(), "scrapingbee": bee_usage()}

def main(out=None):
    s = json.dumps(snapshot(), indent=1)
    if out: open(out, "w").write(s)
    print(s)
