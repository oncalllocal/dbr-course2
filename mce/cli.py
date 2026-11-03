import argparse, sys, csv, datetime, os
from . import scrape, ghl
from .config import *

def cmd_scrape(a):
    trades = [t.strip() for t in a.trades.split(",")]
    cities = [c.strip() for c in a.cities.split(";")]
    queries = [f"{t} in {c}" for c in cities for t in trades]
    leads = scrape.run(queries, a.scrolls, a.keep_franchises)
    for l in leads:
        l["trade"] = next((t for t in trades if t.split()[0].lower() in l["query"].lower()), "")
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    scrape.write_csv(leads, a.out)
    n24 = sum(l["is_24_7"] for l in leads)
    print(f"{len(leads)} leads ({n24} flagged 24/7) -> {a.out}")
    for l in leads[:15]:
        print(f'{l["score"]:>4}  {l["name"][:38]:38} {l["phone"]}  {l["reviews"]:>5} rev  {"24/7" if l["is_24_7"] else l["hours"][:14]}')

def cmd_push(a):
    leads = scrape.read_csv(a.csv)[: a.limit]
    extra = [t for t in (a.tags or "").split(",") if t]
    if a.dry_run:
        print(f"[dry-run] would upsert {len(leads)} contacts with tags {[TAG_PROSPECT, *extra]}"); return
    for l in leads:
        cid, new = ghl.upsert_lead(l, extra)
        if a.queue: ghl.add_tags(cid, [TAG_QUEUE])
        print(("queued " if a.queue else "pushed ") + f'{l["name"]} {cid} new={new}')

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
    s = sub.add_parser("push"); s.set_defaults(f=cmd_push)
    s.add_argument("csv"); s.add_argument("--limit", type=int, default=50)
    s.add_argument("--tags", help="extra tags, comma list"); s.add_argument("--dry-run", action="store_true")
    s.add_argument("--queue", action="store_true", help=f"also add {TAG_QUEUE} (STARTS CALLS if workflow is live)")
    s = sub.add_parser("results"); s.set_defaults(f=cmd_results); s.add_argument("--out", default="data/results.csv")
    a = p.parse_args(); a.f(a)

if __name__ == "__main__": main()
