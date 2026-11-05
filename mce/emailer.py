"""Email 1 to prospects: 'we called last night at <time>', and may we send a short video?

  python3 -m mce email                 # preview only: writes data/email_previews/*.txt, sends nothing
  python3 -m mce email --live          # send through GoHighLevel (needs EMAIL_FROM and POSTAL_ADDRESS)

Safe by default. A live run only sends to contacts that: are tagged mce-no-answer, have an email, are not on the email DND list,
have not already been sent Email 1 (tag mce-email-1-sent), and only Mon-Fri 9:00-11:00 AM Eastern.
"""
import os, re, datetime, html as H
from zoneinfo import ZoneInfo
from . import ghl
from .config import big_job_for

TAG_SENT = "mce-email-1-sent"

def build(contact, fields, sender="Chris", send_date=None):
    name = contact.get("companyName") or contact.get("contactName") or "your company"
    tm, day, outcome = fields.get("call_time") or "7:00 PM", fields.get("call_day") or "", fields.get("outcome") or ""
    when = "last night"
    job = big_job_for(fields.get("source_query")) or fields.get("big_job") or "a big job"
    subject = f"No one picked up at {tm}"
    paras = [
      "Hi there,",
      f"We called {name} {when} at {tm} as part of an after-hours phone audit we're running for local service companies. Nobody picked up.",
      "I'm not writing to scold you. I'm writing because of what that call could have been.",
      f"If that had been a real customer, ready to book {job}, they wouldn't have waited for a callback. They would have hung up and called the next company on Google. And you would never have known the call happened.",
      "That's the part that stings: it isn't the one call, it's that the biggest jobs often come in at the worst times, from people who need an answer right now.",
      "There's a simple fix, and it costs far less than a single job. The moment a call goes unanswered, the caller gets a text from your business. An assistant finds out who they are and what they need, and the whole conversation lands on your phone so you can call them back first.",
      'Would you mind if I sent you a short video (under 5 minutes) showing exactly how it works? Just reply "yes" and I\'ll send it over.',
      f"{sender}<br>OnCall Local",
    ]
    addr = os.environ.get("POSTAL_ADDRESS", "[POSTAL ADDRESS NOT SET]")
    foot = f"OnCall Local &middot; {H.escape(addr)}<br>Not interested? Just reply &quot;no thanks&quot; and we won't email you again."
    html = "".join(f"<p>{p if '<br>' in p else H.escape(p)}</p>" for p in paras) + f'<p style="color:#6b7b8a;font-size:12px">{foot}</p>'
    text = "\n\n".join(re.sub(r"<br>", "\n", p) for p in paras) + "\n\n" + re.sub(r"&middot;", "-", re.sub(r"&quot;", '"', re.sub(r"<br>", "\n", foot)))
    return subject, html, text

def eligible(c):
    tags = {t.lower() for t in c.get("tags", [])}
    dnd = (c.get("dndSettings") or {}).get("Email", {}).get("status") == "active"
    return bool(c.get("email")) and "mce-no-answer" in tags and TAG_SENT not in tags and not c.get("dnd") and not dnd

def in_send_window(now):
    return now.weekday() < 5 and "09:00" <= now.strftime("%H:%M") < "11:00"

def run(args):
    now = datetime.datetime.now(ZoneInfo("America/New_York"))
    todo = [c for c in ghl.contacts_with_tag("mce-no-answer") if eligible(c)][: args.limit]
    print(f"{now:%a %H:%M %Z}; send window Mon-Fri 9-11 AM ET: {'OPEN' if in_send_window(now) else 'CLOSED'}; {len(todo)} eligible prospects")
    os.makedirs(args.out, exist_ok=True); sender = os.environ.get("EMAIL_FROM")
    if args.live:
        if not sender or not os.environ.get("POSTAL_ADDRESS"): raise SystemExit("Set EMAIL_FROM (e.g. 'Sam at OnCall Local <sam@yourdomain>') and POSTAL_ADDRESS before sending.")
        if not in_send_window(now) and not args.ignore_window: raise SystemExit("Outside the send window; nothing sent.")
    sent = 0
    for c in todo:
        full = ghl.call("GET", f"/contacts/{c['id']}")["contact"]; f = ghl.field_values(full)
        subject, html, text = build(full, f)
        slug = re.sub(r"[^a-z0-9]+", "_", (full.get("companyName") or c["id"]).lower()).strip("_")
        open(f"{args.out}/{slug}.txt", "w").write(f"To: {full['email']}\nSubject: {subject}\n\n{text}\n")
        if not args.live: print(f"  [preview] {full.get('companyName')} <{full['email']}>  ->  {args.out}/{slug}.txt"); continue
        ghl.call("POST", "/conversations/messages", json={"type": "Email", "contactId": c["id"], "subject": subject, "html": html, "emailFrom": sender})
        ghl.add_tags(c["id"], [TAG_SENT]); ghl.add_note(c["id"], f"EMAIL 1 SENT {now:%a %b %-d %-I:%M %p ET}\nSubject: {subject}\n\n{text}"); sent += 1; print("  sent:", full.get("companyName"))
    print(f"{'sent' if args.live else 'previewed'}: {sent if args.live else len(todo)}")
