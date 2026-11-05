"""Find prospect replies to Email 1, classify them, and act (never sends anything).

  python3 -m mce replies                 # dry run: shows what it found and what it would do
  python3 -m mce replies --act           # apply: tags, DND for opt-outs, notes, tasks
  python3 -m mce replies --contact ID    # look at one contact only (works for the test contact)
"""
import re, html
from . import ghl

NEG = re.compile(r"\b(no thanks|no thank you|not interested|unsubscribe|remove me|take me off|stop (emailing|sending|contacting)|stop\b|don'?t (email|contact|send)|do not (email|contact|send)|leave me alone|opt.?out)\b", re.I)
POS = re.compile(r"\b(yes|yep|yeah|yup|sure|please do|please send|go ahead|send (it|me|the)|interested|sounds good|tell me more|okay|ok\b|absolutely|definitely|i'?d like|would like to see)\b", re.I)
CUT = re.compile(r"(^|\n)\s*(From:|On .{0,120}wrote:|-{2,}\s*Original|_{5,}|Sent from my|>)", re.I)

def clean(body):
    """Reply text only: drop CSS, tags, the quoted original and the signature block."""
    t = re.sub(r"<style.*?</style>", "", body or "", flags=re.S | re.I)
    t = re.sub(r"<(br|/p|/div|/tr)[^>]*>", "\n", t, flags=re.I); t = html.unescape(re.sub(r"<[^>]+>", "", t))
    t = re.sub(r"^[^\n]*\{[^}]*\}\s*", "", t) if t.lstrip().startswith(("P {", "p {")) else t     # leading CSS rule some clients add
    t = re.sub(r"[ \t\r\xa0]+", " ", t); t = re.sub(r"\n\s*\n+", "\n", t).strip()
    m = CUT.search(t); t = t[:m.start()] if m else t
    return re.sub(r"\n(Thanks|Thank you|Best|Regards|Sincerely),?\s*\n.*$", "", t, flags=re.S | re.I).strip()

def classify(text):
    if not text: return "review"
    if NEG.search(text): return "no"
    if POS.search(text) and len(text.split()) <= 60: return "yes"
    return "review"

def inbound_email(contact_id):
    """Latest inbound email from this contact: (reply text, date, email id) or None."""
    convs = ghl.call("GET", "/conversations/search", params={"locationId": ghl.ghl_location(), "contactId": contact_id}).get("conversations", [])
    best = None
    for cv in convs:
        m = ghl.call("GET", f"/conversations/{cv['id']}/messages", params={"limit": 30})
        msgs = (m.get("messages") or {}).get("messages", []) if isinstance(m.get("messages"), dict) else m.get("messages", [])
        for x in msgs:
            if x.get("direction") == "inbound" and x.get("messageType") == "TYPE_EMAIL" and (best is None or x["dateAdded"] > best["dateAdded"]): best = x
    if not best: return None
    ids = ((best.get("meta") or {}).get("email") or {}).get("messageIds") or []
    for mid in list(reversed(ids)) + [best["id"]]:          # the email record is filed under the ids in meta, newest last
        try:
            e = ghl.call("GET", f"/conversations/messages/email/{mid}"); e = e.get("emailMessage", e)
            if e.get("direction") == "inbound": return clean(e.get("body") or best.get("body")), best["dateAdded"], mid
        except Exception: continue
    return clean(best.get("body")), best["dateAdded"], best["id"]

def scan(args):
    if args.contact: cands = [ghl.call("GET", f"/contacts/{args.contact}")["contact"]]
    else: cands = [c for c in ghl.contacts_with_tag("mce-email-1-sent") if "mce-reply-processed" not in [t.lower() for t in c.get("tags", [])]]
    print(f"{len(cands)} contact(s) to check")
    interested = []
    for c in cands:
        r = inbound_email(c["id"]); name = c.get("companyName") or c.get("contactName")
        if not r: continue
        text, when, mid = r; kind = classify(text)
        print(f"  {name}: {kind.upper()}  reply: {text[:100]!r}")
        if not args.act: continue
        cid = c["id"]
        ghl.add_note(cid, f"REPLY RECEIVED {when}\nClassified: {kind}\n\n{text}")
        ghl.add_tags(cid, ["mce-replied", "mce-reply-processed"])
        if kind == "no":
            ghl.add_tags(cid, ["mce-dnc"]); ghl.call("PUT", f"/contacts/{cid}", json={"dndSettings": {"Email": {"status": "active", "message": "Opted out by reply", "code": "101"}}})
        elif kind == "yes":
            ghl.add_tags(cid, ["mce-interested"]); interested.append(cid); print(f"INTERESTED:{cid}:{name}")
        else:
            ghl.add_tags(cid, ["mce-reply-review"]); ghl.add_task(cid, f"Read reply from {name}", f"Could not tell if this is a yes or a no:\n\n{text}", __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"))
    return interested
