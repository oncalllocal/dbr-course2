"""After-hours prospecting dialer on Twilio.

Reads contacts tagged `mce-dial-queue` from GHL (mobile numbers never carry that tag), places one call each
inside the calling window, plays the message to a live answer, and records the outcome back into GHL.

Outcomes
  answered   a person (or live answering service) picked up      -> tag mce-answered, queue tag removed
  voicemail  a machine/voicemail picked up                        -> counts as a miss
  ringout    no answer / busy / failed                            -> counts as a miss
A lead becomes a prospect (`mce-no-answer` + task) after MISSES_NEEDED misses on different evenings.

Safe by default: nothing is dialed unless you pass --live.
"""
import os, sys, time, datetime, json, requests
from zoneinfo import ZoneInfo
from . import ghl, notes
from .config import *

API = "https://api.twilio.com/2010-04-01/Accounts/{sid}"
TERMINAL = {"completed", "busy", "failed", "no-answer", "canceled"}
MISSES_NEEDED = 2
DAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
MESSAGE = ("Hi, this is OnCall Local calling to check after-hours phone availability for local service "
           "businesses. No action is needed on your part. Thank you, and have a good evening.")
TAG_ATTEMPT = "mce-attempt-1"      # one miss recorded
TAG_DNC = "mce-dnc"

def twilio_env():
    return {k: os.environ.get(k) for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER")}

def in_window(now, days, start, end):
    """now: aware datetime in the lead's zone; days like 'mon-thu'; start/end 'HH:MM'."""
    a, b = (days.lower().split("-") + [days.lower()])[:2] if "-" in days else (days.lower(), days.lower())
    d = now.weekday()
    ok_day = DAYS[a[:3]] <= d <= DAYS[b[:3]]
    hm = now.strftime("%H:%M")
    return ok_day and start <= hm < end

def outcome(status, answered_by):
    """Map a Twilio call result to answered / voicemail / ringout."""
    if status != "completed": return "ringout"
    if (answered_by or "").startswith("machine") or answered_by == "fax": return "voicemail"
    return "answered"            # human, unknown, or no AMD result: do not pester or mark as a prospect

def twiml(leave_voicemail=False):
    # DetectMessageEnd holds this TwiML until the voicemail greeting finishes (after the beep), so the whole message is recorded.
    return f'<Response><Pause length="1"/><Say voice="Polly.Joanna-Neural">{MESSAGE}</Say><Hangup/></Response>'

def place(to, from_, voicemail):
    env = twilio_env(); base = API.format(sid=env["TWILIO_ACCOUNT_SID"]); auth = (env["TWILIO_ACCOUNT_SID"], env["TWILIO_AUTH_TOKEN"])
    r = requests.post(f"{base}/Calls.json", auth=auth, timeout=30, data={
        "To": to, "From": from_, "Twiml": twiml(voicemail), "Timeout": 30,
        "MachineDetection": "DetectMessageEnd", "MachineDetectionTimeout": 30})
    if r.status_code >= 300: raise RuntimeError(f"Twilio {r.status_code}: {r.text[:200]}")
    sid = r.json()["sid"]; end = time.time() + 120
    while time.time() < end:
        c = requests.get(f"{base}/Calls/{sid}.json", auth=auth, timeout=30).json()
        if c["status"] in TERMINAL:
            return outcome(c["status"], c.get("answered_by")), c
        time.sleep(3)
    return "ringout", {"status": "timeout"}

def load_queue(args):
    if args.from_csv:
        from .scrape import read_csv
        rows = [r for r in read_csv(args.from_csv) if r.get("line_type") in ("landline", "voip", "tollfree") or args.allow_unknown]
        return [{"id": None, "name": r["name"], "phone": r["phone"], "tags": []} for r in rows]
    out = []
    for c in ghl.contacts_with_tag(TAG_QUEUE):
        tags = [t.lower() for t in c.get("tags", [])]
        if TAG_DNC in tags or c.get("dnd") or TAG_CELL_MANUAL in tags: continue
        out.append({"id": c["id"], "name": c.get("companyName") or c.get("contactName"), "phone": c.get("phone"), "tags": tags})
    return out

def record(c, result, call_day, call=None, tz="America/New_York"):
    cid = c["id"]
    if not cid: return
    full = ghl.call("GET", f"/contacts/{cid}")["contact"]; fields = ghl.field_values(full)
    attempt = 2 if TAG_ATTEMPT in c["tags"] else 1
    prospect = result != "answered" and attempt == 2
    when = datetime.datetime.now(ZoneInfo(tz))
    ids = ghl.field_ids(); cf = [{"id": ids[k], "field_value": v} for k, v in
          (("outcome", result), ("call_day", call_day), ("call_time", when.strftime("%-I:%M %p"))) if ids.get(k)]
    if cf: ghl.call("PUT", f"/contacts/{cid}", json={"customFields": cf})
    try: ghl.add_note(cid, notes.call_note(full, fields, result, attempt, call, MESSAGE, tz, prospect))
    except Exception as e: print("  note warn:", str(e)[:120])
    if result in ("voicemail", "ringout"): ghl.add_tags(cid, ["mce-" + result])
    if result == "answered":
        ghl.add_tags(cid, [TAG_ANSWERED]); ghl.call("DELETE", f"/contacts/{cid}/tags", json={"tags": [TAG_QUEUE]})
    elif prospect:
        ghl.add_tags(cid, [TAG_NOANSWER]); ghl.call("DELETE", f"/contacts/{cid}/tags", json={"tags": [TAG_QUEUE, TAG_ATTEMPT]})
        prev = f"{fields.get('call_day','?')} {fields.get('call_time','')}".strip() + f": {fields.get('outcome','missed')}"
        history = [prev, f"{when.strftime('%A %-I:%M %p')}: {result}"]
        due = (datetime.datetime.utcnow() + datetime.timedelta(days=1)).strftime("%Y-%m-%dT14:00:00.000Z")
        ghl.add_task(cid, f"Call {c['name']}: missed our after-hours call (2 evenings)", notes.prospect_task(full, fields, history, tz), due)
    else:
        ghl.add_tags(cid, [TAG_ATTEMPT])

def sms_owner(text):
    to, env = os.environ.get("OWNER_PHONE"), twilio_env()
    if not to: print("(no OWNER_PHONE set; skipping SMS digest)"); return
    requests.post(API.format(sid=env["TWILIO_ACCOUNT_SID"]) + "/Messages.json", auth=(env["TWILIO_ACCOUNT_SID"], env["TWILIO_AUTH_TOKEN"]),
                  data={"To": to, "From": env["TWILIO_FROM_NUMBER"], "Body": text[:1500]}, timeout=30)

def run(args):
    tz = ZoneInfo(args.tz); now = datetime.datetime.now(tz)
    queue = load_queue(args)[: args.limit]
    open_now = in_window(now, args.days, args.start, args.end)
    print(f"{now:%a %H:%M %Z}; window {args.days} {args.start}-{args.end}: {'OPEN' if open_now else 'CLOSED'}; {len(queue)} in queue")
    if not args.live:
        for c in queue: print(f"  [dry-run] would call {c['name']} {c['phone']}")
        print("Dry run only. Add --live to dial."); return
    env = twilio_env()
    if not all(env.values()): sys.exit("Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER")
    if not open_now and not args.ignore_window: sys.exit("Outside the calling window; nothing dialed (use --ignore-window only for your own test number).")
    stats, misses = {"answered": 0, "voicemail": 0, "ringout": 0}, []
    for c in queue:
        if not in_window(datetime.datetime.now(tz), args.days, args.start, args.end) and not args.ignore_window:
            print("window closed; stopping"); break
        try: res, call = place(c["phone"], env["TWILIO_FROM_NUMBER"], False)
        except Exception as e: print("  error:", str(e)[:150]); continue
        stats[res] += 1; print(f"  {c['name']} {c['phone']} -> {res}")
        if res != "answered": misses.append(c["name"])
        try: record(c, res, f"{now:%A}", call, args.tz)
        except Exception as e: print("  ghl warn:", str(e)[:150])
        time.sleep(args.pace)
    print(stats)
    if args.sms: sms_owner(f"MCTB dialer: {stats}. Missed: " + "; ".join(misses[:15]))
