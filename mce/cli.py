import argparse, sys, csv, datetime, os
from . import scrape, ghl, lineinfo, enrich, dialer
from .config import *

def cmd_scrape(a):
    trades = [t.strip() for t in a.trades.split(",")]
    cities = [c.strip() for c in a.cities.split(";")]
    queries = [f"{t} in {c}" for c in cities for t in trades]
    leads = scrape.run(queries, a.scrolls, a.keep_franchises)
    for l in leads:
        l["trade"] = next((t for t in trades if t.split()[0].lower() in l["query"].lower()), "")
    if a.lookup: lineinfo.classify_all(leads)
    if a.enrich: print(f"emails found: {enrich.enrich_all(leads)}/{len(leads)}")
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    scrape.write_csv(leads, a.out)
    n24 = sum(l["is_24_7"] for l in leads)
    print(f"{len(leads)} leads ({n24} flagged 24/7) -> {a.out}")
    for l in leads[:15]:
        print(f'{l["score"]:>4}  {l["name"][:38]:38} {l["phone"]}  {l["reviews"]:>5} rev  {"24/7" if l["is_24_7"] else l["hours"][:14]}')

def _rewrite(path, leads):
    scrape.write_csv(leads, path)

def cmd_lookup(a):
    leads = scrape.read_csv(a.csv)
    if not lineinfo.provider(): print("No lookup provider configured (set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN). Only toll-free can be detected.")
    lineinfo.classify_all(leads); _rewrite(a.csv, leads)
    from collections import Counter; print(dict(Counter(l["line_type"] for l in leads)))

def cmd_enrich(a):
    leads = scrape.read_csv(a.csv); n = enrich.enrich_all(leads); _rewrite(a.csv, leads)
    print(f"emails found: {n}/{len(leads)}")

def _due_tomorrow_9am():
    d = datetime.datetime.utcnow().date() + datetime.timedelta(days=1)
    return datetime.datetime(d.year, d.month, d.day, 14, 0).strftime("%Y-%m-%dT%H:%M:%S.000Z")  # 9 AM Central

def cmd_push(a):
    leads = scrape.read_csv(a.csv)[: a.limit]
    extra = [t for t in (a.tags or "").split(",") if t]
    if a.dry_run:
        from collections import Counter
        print(f"[dry-run] would upsert {len(leads)} contacts; line types {dict(Counter(l.get('line_type') or 'unknown' for l in leads))}")
        print(f"[dry-run] mobile -> manual-call (tag {TAG_CELL_MANUAL}, task, pipeline stage); others -> dial queue only with --queue"); return
    if a.skip_tollfree: leads = [l for l in leads if l.get("line_type") != "tollfree"]
    stage = ghl.pipeline_stage(PIPELINE_NAME, STAGE_MANUAL)
    if not stage: print(f'note: pipeline "{PIPELINE_NAME}" with stage "{STAGE_MANUAL}" not found; cell leads get the tag + a task only')
    counts = {"queued": 0, "manual": 0, "held": 0, "pushed": 0}
    for l in leads:
        cid, new = ghl.upsert_lead(l, extra)
        lt = l.get("line_type") or "unknown"
        if lt == "mobile":                       # never auto-dialed; owner calls by hand
            counts["manual"] += 1
            try:
                ghl.add_task(cid, f'Call (cell) {l["name"]}', f'{l["phone"]} | {l.get("website","")} | {l.get("email","")}', _due_tomorrow_9am())
                if stage: ghl.add_opportunity(cid, l["name"], *stage)
            except Exception as e: print("  warn:", str(e)[:160])
            print(f'manual-call {l["name"]} {l["phone"]}')
        elif a.queue and (lt != "unknown" or a.allow_unknown):
            ghl.add_tags(cid, [TAG_QUEUE]); counts["queued"] += 1
            print(f'queued {l["name"]} {lt}')
        elif a.queue:
            counts["held"] += 1; print(f'held (line type unknown, use --allow-unknown) {l["name"]}')
        else:
            counts["pushed"] += 1; print(f'pushed {l["name"]} {lt}')
    print(counts)

def cmd_results(a):
    rows = []
    for tag, label in ((TAG_NOANSWER, "NO ANSWER"), (TAG_ANSWERED, "ANSWERED")):
        for c in ghl.list_contacts(tag):
            rows.append({"outcome": label, "name": c.get("companyName") or c.get("contactName"),
                         "phone": c.get("phone"), "tags": ",".join(c.get("tags", []))})
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    w = csv.DictWriter(open(a.out, "w", newline=""), ["outcome","name","phone","tags"]); w.writeheader(); w.writerows(rows)
    na = sum(r["outcome"] == "NO ANSWER" for r in rows)
    print(f"{len(rows)} results: {na} no-answer (prospects), {len(rows)-na} answered -> {a.out}")

def main():
    p = argparse.ArgumentParser(prog="mce"); sub = p.add_subparsers(required=True)
    s = sub.add_parser("scrape"); s.set_defaults(f=cmd_scrape)
    s.add_argument("--trades", required=True, help='comma list, e.g. "plumber,hvac contractor"')
    s.add_argument("--cities", required=True, help='semicolon list, e.g. "Tampa FL;Orlando FL"')
    s.add_argument("--scrolls", type=int, default=6); s.add_argument("--keep-franchises", action="store_true")
    s.add_argument("--out", default="data/leads.csv")
    s.add_argument("--lookup", action="store_true", help="classify line type (mobile/landline/voip/tollfree)")
    s.add_argument("--enrich", action="store_true", help="find a public email on each lead's website")
    s = sub.add_parser("lookup"); s.set_defaults(f=cmd_lookup); s.add_argument("csv")
    s = sub.add_parser("enrich"); s.set_defaults(f=cmd_enrich); s.add_argument("csv")
    s = sub.add_parser("push"); s.set_defaults(f=cmd_push)
    s.add_argument("csv"); s.add_argument("--limit", type=int, default=50)
    s.add_argument("--tags", help="extra tags, comma list"); s.add_argument("--dry-run", action="store_true")
    s.add_argument("--allow-unknown", action="store_true", help="auto-dial numbers whose line type is unknown")
    s.add_argument("--skip-tollfree", action="store_true", help="leave toll-free numbers out of the import")
    s.add_argument("--queue", action="store_true", help=f"also add {TAG_QUEUE} (STARTS CALLS if workflow is live)")
    s = sub.add_parser("dial", help="Twilio after-hours dialer (dry run unless --live)"); s.set_defaults(f=lambda a: dialer.run(a))
    s.add_argument("--live", action="store_true"); s.add_argument("--limit", type=int, default=25)
    s.add_argument("--from-csv", help="dry-run/test against a CSV instead of the GHL queue"); s.add_argument("--allow-unknown", action="store_true")
    s.add_argument("--tz", default="America/New_York"); s.add_argument("--days", default="mon-thu")
    s.add_argument("--start", default="17:30"); s.add_argument("--end", default="20:30")
    s.add_argument("--pace", type=int, default=8, help="seconds between calls"); s.add_argument("--sms", action="store_true", help="text a summary to OWNER_PHONE")
    s.add_argument("--leave-voicemail", action="store_true"); s.add_argument("--ignore-window", action="store_true")
    s = sub.add_parser("results"); s.set_defaults(f=cmd_results); s.add_argument("--out", default="data/results.csv")
    a = p.parse_args(); a.f(a)

if __name__ == "__main__": main()
