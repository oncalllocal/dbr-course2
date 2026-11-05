import argparse, sys, csv, datetime, os
from . import scrape, ghl, lineinfo, enrich, dialer, notes, status
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

def cmd_cells(a):
    stage = ghl.pipeline_stage(PIPELINE_NAME, STAGE_MANUAL)
    if not stage: sys.exit(f'pipeline "{PIPELINE_NAME}" / stage "{STAGE_MANUAL}" not found')
    for c in ghl.list_contacts(TAG_CELL_MANUAL):
        have = ghl.call("GET", "/opportunities/search", params={"location_id": ghl.ghl_location(), "contact_id": c["id"], "pipeline_id": stage[0]}).get("opportunities", [])
        name = c.get("companyName") or c.get("contactName")
        if have: print("already in pipeline:", name); continue
        ghl.add_opportunity(c["id"], name, *stage); print("added:", name)

def cmd_promote(a):
    todo = [c for c in ghl.contacts_with_tag("mce-attempt-1") if "mce-no-answer" not in [t.lower() for t in c.get("tags", [])] and "mce-answered" not in [t.lower() for t in c.get("tags", [])]]
    print(f"{len(todo)} leads missed once and are not yet prospects")
    due = _next_business_day_9am_utc()
    for c in todo:
        full = ghl.call("GET", f"/contacts/{c['id']}")["contact"]; f = ghl.field_values(full); name = full.get("companyName") or full.get("contactName")
        if "mce-no-answer" in [t.lower() for t in full.get("tags", [])]: continue      # search index lags; the contact itself is the truth
        hist = [f"{f.get('call_day','?')} {f.get('call_time','')}".strip() + f": {f.get('outcome','missed')}"]
        if a.dry_run: print("  [dry-run]", name, hist[0]); continue
        ghl.add_tags(c["id"], ["mce-no-answer"]); ghl.call("DELETE", f"/contacts/{c['id']}/tags", json={"tags": ["mce-dial-queue", "mce-attempt-1"]})
        ghl.add_task(c["id"], f"Call {name}: missed our after-hours call", notes.prospect_task(full, f, hist, "America/New_York"), due)
        try: ghl.ensure_opportunity(c["id"], name, "Did not answer")
        except Exception as e: print("  pipeline warn:", str(e)[:120])
        ghl.add_note(c["id"], "Promoted to PROSPECT: owner changed the rule to one missed call. " + hist[0]); print("  promoted:", name, hist[0])

def cmd_rescore(a):
    leads = scrape.rescore(scrape.read_csv(a.csv)); _rewrite(a.csv, leads); print(f"rescored {len(leads)} leads")

def cmd_enrich(a):
    leads = scrape.read_csv(a.csv); n = enrich.enrich_all(leads); _rewrite(a.csv, leads)
    print(f"emails found: {n}/{len(leads)}")

def _due_tomorrow_9am():
    d = datetime.datetime.utcnow().date() + datetime.timedelta(days=1)
    return datetime.datetime(d.year, d.month, d.day, 14, 0).strftime("%Y-%m-%dT%H:%M:%S.000Z")  # 9 AM Central

def _next_business_day_9am_utc():
    from zoneinfo import ZoneInfo
    d = datetime.datetime.now(ZoneInfo("America/New_York")).date() + datetime.timedelta(days=1)
    while d.weekday() >= 5: d += datetime.timedelta(days=1)
    return datetime.datetime(d.year, d.month, d.day, 9, tzinfo=ZoneInfo("America/New_York")).astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

def cmd_push(a):
    leads = scrape.read_csv(a.csv)
    leads = [l for l in leads if l["score"] >= a.min_score and not (a.skip_tollfree and l.get("line_type") == "tollfree")]
    leads = leads[: a.limit] if a.limit else leads
    extra = [t for t in (a.tags or "").split(",") if t]
    from collections import Counter
    lt = Counter(l.get("line_type") or "unknown" for l in leads)
    if a.dry_run:
        print(f"[dry-run] would upsert {len(leads)} contacts (score >= {a.min_score}); line types {dict(lt)}")
        print(f"[dry-run] mobile -> manual list (tag {TAG_CELL_MANUAL} + pipeline stage; tasks come from `mce manual-tasks`); VoIP/landline -> dial queue only with --queue"); return
    stage = ghl.pipeline_stage(PIPELINE_NAME, STAGE_MANUAL)
    if not stage: print(f'note: pipeline "{PIPELINE_NAME}" / stage "{STAGE_MANUAL}" not found; cell leads get the tag only')
    counts = {"queued": 0, "manual": 0, "held": 0, "pushed": 0, "skipped_already_worked": 0}
    for l in leads:                                  # already sorted best-first by the scraper
        cid, new, tags = ghl.upsert_lead(l, extra)
        kind = l.get("line_type") or "unknown"
        if kind == "mobile":                         # never auto-dialed
            counts["manual"] += 1
            try:
                if stage: ghl.ensure_opportunity(cid, l["name"], STAGE_MANUAL)
            except Exception as e: print("  warn:", str(e)[:160])
        elif a.queue and (kind != "unknown" or a.allow_unknown):
            if {"mce-answered", "mce-no-answer", "mce-dnc", "mce-test"} & set(tags) or "mce-dial-queue" in tags:
                counts["skipped_already_worked"] += 1; continue      # never re-queue someone already called or opted out
            ghl.add_tags(cid, [TAG_QUEUE]); counts["queued"] += 1
        elif a.queue: counts["held"] += 1
        else: counts["pushed"] += 1
    print(counts)

def cmd_manual_tasks(a):
    """Create call tasks for the best untasked mobile leads, up to --per-day, due the next business day 9 AM Eastern."""
    sid = ghl.field_ids().get("score")
    cells = [c for c in ghl.contacts_with_tag(TAG_CELL_MANUAL)
             if TAG_MANUAL_TASKED not in [t.lower() for t in c.get("tags", [])]
             and "mce-dnc" not in [t.lower() for t in c.get("tags", [])] and not c.get("dnd")]
    key = lambda c: -next((float(f.get("value") or 0) for f in c.get("customFields", []) if f.get("id") == sid), 0.0)
    todo = sorted(cells, key=key)[: a.per_day]
    print(f"{len(cells)} cell leads without a task; creating {len(todo)} (limit {a.per_day}/day)")
    due = _next_business_day_9am_utc()
    for c in todo:
        full = ghl.call("GET", f"/contacts/{c['id']}")["contact"]; f = ghl.field_values(full)
        name = full.get("companyName") or full.get("contactName")
        if a.dry_run: print(f"  [dry-run] {name} score {f.get('score')}"); continue
        ghl.add_task(c["id"], f"Call (cell) {name}", notes.manual_task(full, f), due)
        ghl.add_tags(c["id"], [TAG_MANUAL_TASKED]); print(f"  task: {name}")

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
    s = sub.add_parser("cells-to-pipeline", help="put every mce-cell-manual contact into the Manual Call stage (skips ones already there)"); s.set_defaults(f=cmd_cells)
    s = sub.add_parser("promote-misses", help="make every lead that already missed once a prospect (rule changed to one miss)"); s.set_defaults(f=cmd_promote); s.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("rescore"); s.set_defaults(f=cmd_rescore); s.add_argument("csv")
    s = sub.add_parser("enrich"); s.set_defaults(f=cmd_enrich); s.add_argument("csv")
    s = sub.add_parser("push"); s.set_defaults(f=cmd_push)
    s.add_argument("csv"); s.add_argument("--limit", type=int, default=0, help="0 = every lead that qualifies")
    s.add_argument("--min-score", type=int, default=MIN_SCORE)
    s.add_argument("--tags", help="extra tags, comma list"); s.add_argument("--dry-run", action="store_true")
    s.add_argument("--allow-unknown", action="store_true", help="auto-dial numbers whose line type is unknown")
    s.add_argument("--skip-tollfree", action="store_true", help="leave toll-free numbers out of the import")
    s.add_argument("--queue", action="store_true", help=f"also add {TAG_QUEUE} (STARTS CALLS if workflow is live)")
    s = sub.add_parser("dial", help="Twilio after-hours dialer (dry run unless --live)"); s.set_defaults(f=lambda a: dialer.run(a))
    s.add_argument("--live", action="store_true"); s.add_argument("--limit", type=int, default=25)
    s.add_argument("--from-csv", help="dry-run/test against a CSV instead of the GHL queue"); s.add_argument("--allow-unknown", action="store_true")
    s.add_argument("--tz", default="America/New_York"); s.add_argument("--days", default="mon-thu")
    s.add_argument("--start", default="19:00"); s.add_argument("--end", default="19:45")
    s.add_argument("--pace", type=int, default=8, help="seconds between calls"); s.add_argument("--sms", action="store_true", help="text a summary to OWNER_PHONE")
    s.add_argument("--ignore-window", action="store_true")
    s = sub.add_parser("manual-tasks", help="create the daily batch of manual-call tasks (best scores first)"); s.set_defaults(f=cmd_manual_tasks)
    s.add_argument("--per-day", type=int, default=MANUAL_PER_DAY); s.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("status", help="read-only system snapshot as JSON"); s.set_defaults(f=lambda a: status.main(a.out)); s.add_argument("--out")
    s = sub.add_parser("results"); s.set_defaults(f=cmd_results); s.add_argument("--out", default="data/results.csv")
    a = p.parse_args(); a.f(a)

if __name__ == "__main__": main()
