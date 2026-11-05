"""Turn an interested reply into a REVIEW-READY draft: personalized video + Email 2. Nothing is sent to the prospect.

  python3 -m mce draft --contact ID            # build the video, upload it to the GHL media library, save Email 2 as a draft note + a review task
  python3 -m mce send-video --contact ID       # ONLY after the owner approves: sends the saved Email 2
"""
import os, re, subprocess, datetime, html as H, requests
from . import ghl, emailer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUBJECT = "Your video: what a missed call really costs"
MARK = "DRAFT EMAIL 2 (NOT SENT)"

def slug_for(name): return "".join(ch if ch.isalnum() else "_" for ch in name.lower()).strip("_")

def upload(path, name):
    H_ = {"Authorization": f"Bearer {ghl.ghl_token()}", "Version": "2021-07-28", "Accept": "application/json"}
    r = requests.post("https://services.leadconnectorhq.com/medias/upload-file", headers=H_, timeout=600,
                      files={"file": (name, open(path, "rb"), "video/mp4")}, data={"name": name, "hosted": "false"})
    if r.status_code >= 300: raise RuntimeError(f"media upload {r.status_code}: {r.text[:200]}")
    return r.json()["url"]

def body(url, first=None):
    greet = f"Hi {first}," if first else "Hi there,"
    paras = [greet, "Thanks for saying yes. Here's the video (under 5 minutes):", f'<a href="{H.escape(url)}">{H.escape(url)}</a>',
             "It covers what an unanswered after-hours call can cost, how the text-back works, and founder pricing: $497 for the first month, then $247 a month, no contract.",
             "If it makes sense, just reply to this email and I'll get you set up. If you have questions, reply with those instead.", "Chris<br>OnCall Local"]
    addr = os.environ.get("POSTAL_ADDRESS", emailer.DEFAULT_POSTAL)
    foot = f'<p style="color:#6b7b8a;font-size:12px">OnCall Local &middot; {H.escape(addr)}<br>Not interested? Just reply "no thanks" and we won\'t email you again.</p>'
    html = "".join(f"<p>{p}</p>" if p.startswith("<a") or "<br>" in p else f"<p>{H.escape(p)}</p>" for p in paras) + foot
    text = f"{greet}\n\nThanks for saying yes. Here's the video (under 5 minutes):\n\n{url}\n\nIt covers what an unanswered after-hours call can cost, how the text-back works, and founder pricing: $497 for the first month, then $247 a month, no contract.\n\nIf it makes sense, just reply to this email and I'll get you set up. If you have questions, reply with those instead.\n\nChris\nOnCall Local"
    return html, text

def draft(args):
    c = ghl.call("GET", f"/contacts/{args.contact}")["contact"]; name = c.get("companyName") or c.get("contactName"); slug = slug_for(name)
    tags = {t.lower() for t in c.get("tags", [])}
    if "mce-video-ready" in tags and not args.force: raise SystemExit(f"{name} already has a draft ready. Use --force to rebuild.")
    mp4 = f"{ROOT}/out/{slug}.mp4"
    if not args.skip_build:
        print(f"building the video for {name} (about 6 minutes)...")
        subprocess.check_call(["python3", f"{ROOT}/tools/build_vsl.py", "--contact", args.contact], cwd=ROOT)
    if not os.path.exists(mp4): raise SystemExit(f"video not found: {mp4}")
    url = upload(mp4, f"{slug}.mp4"); html, text = body(url, ghl.field_values(c).get("owner_first"))
    ghl.add_note(args.contact, f"{MARK}\nTo: {c.get('email') or '(no email on file)'}\nSubject: {SUBJECT}\nVIDEO: {url}\n\n{text}")
    ghl.add_task(args.contact, f"REVIEW & SEND video + email: {name}", f"Their reply said yes. A personalized video and Email 2 are ready as a DRAFT. NOTHING has been sent.\n\nVideo: {url}\n\nTo: {c.get('email') or '(no email on file)'}\nSubject: {SUBJECT}\n\n{text}\n\nWhen you approve, tell Claude to send it.",
                 datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"))
    ghl.add_tags(args.contact, ["mce-video-ready"])
    try: ghl.ensure_opportunity(args.contact, name, "Contacted")
    except Exception as e: print("pipeline note:", str(e)[:100])
    notify_owner(name, c, url, text)
    print(f"DRAFT READY for {name}\n  video: {url}\n  email: saved as a note + review task (not sent)")
    return url

def send_video(args):
    c = ghl.call("GET", f"/contacts/{args.contact}")["contact"]; name = c.get("companyName") or c.get("contactName")
    notes = ghl.call("GET", f"/contacts/{args.contact}/notes").get("notes", [])
    n = next((x for x in sorted(notes, key=lambda x: x.get("dateAdded", ""), reverse=True) if MARK in x.get("body", "")), None)
    if not n: raise SystemExit("no saved draft found for this contact")
    if "mce-video-sent" in {t.lower() for t in c.get("tags", [])} and not args.force: raise SystemExit("already sent")
    if not c.get("email"): raise SystemExit("this contact has no email on file")
    url = re.search(r"VIDEO: (\\S+)", n["body"]).group(1); html, text = body(url, ghl.field_values(c).get("owner_first"))
    ghl.call("POST", "/conversations/messages", json={"type": "Email", "contactId": args.contact, "subject": SUBJECT, "html": html, "emailFrom": os.environ.get("EMAIL_FROM", emailer.DEFAULT_FROM)})
    ghl.add_tags(args.contact, ["mce-video-sent"]); ghl.add_note(args.contact, f"EMAIL 2 SENT (video)\nVIDEO: {url}"); print(f"sent Email 2 to {name} <{c['email']}>")


OWNER_EMAIL = "chris@oncalllocal.com"

def notify_owner(name, contact, url, text):
    """Email the owner that a draft is ready for review. Goes to the owner's own address only, never to the prospect."""
    try:
        owner = next((c for c in ghl.contacts_with_tag("mce-test") if (c.get("email") or "").lower() == OWNER_EMAIL), None)
        if not owner: print("owner notice skipped: no test contact with the owner's email"); return
        link = f"https://app.gohighlevel.com/v2/location/{ghl.ghl_location()}/contacts/detail/{contact['id']}"
        body_html = (f"<p><b>Draft ready for review: {H.escape(name)}</b></p><p>They replied yes. Nothing has been sent to them.</p>"
                     f'<p>Video: <a href="{H.escape(url)}">{H.escape(url)}</a></p><p>Open their contact (the draft email is in their notes and review task): <a href="{link}">{link}</a></p>'
                     f"<p>When you approve, tell Claude to send.</p><hr><pre style=\"white-space:pre-wrap\">{H.escape(text)}</pre>")
        ghl.call("POST", "/conversations/messages", json={"type": "Email", "contactId": owner["id"], "subject": f"[DRAFT READY] {name}", "html": body_html, "emailFrom": os.environ.get("EMAIL_FROM", emailer.DEFAULT_FROM)})
        print("owner notified by email")
    except Exception as e: print("owner notice failed:", str(e)[:120])
