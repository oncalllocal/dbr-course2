#!/usr/bin/env python3
"""Build one personalized video sales letter.

  python3 tools/build_vsl.py --niche plumber --biz "Dyser Plumbing Co" --slug dyser_plumbing [--skip-render] [--md out.md]

Only the trade-specific lines change per niche (the emergency, the search, the big job, the payback math, the animation).
Everything else is shared, so its voiceover is cached and a second video in the same niche costs no new voice characters.
The company name appears on screen only (never spoken), so pronunciation can't go wrong.
"""
import argparse, json, os, subprocess, sys, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NICHES = {  # job_stat/job_label: on-screen; job_spoken: narration; job_short: used in the payback line
 "plumber":      dict(emergency="has water coming through the ceiling", short="They've got water coming through the ceiling.", search="search for a plumber", on_job="under a sink",
                      job_stat="$12,000", job_label="whole-home repipe", job_spoken="a twelve thousand dollar repipe", job_short="twelve thousand dollar repipe", price=12000),
 "hvac":         dict(emergency="has no air conditioning in ninety-five degree heat", short="It's ninety-five degrees in that house.", search="search for an A C repair company", on_job="in a hot attic",
                      job_stat="$15,000", job_label="HVAC system replacement", job_spoken="a fifteen thousand dollar H V A C system replacement", job_short="fifteen thousand dollar system replacement", price=15000),
 "electrician":  dict(emergency="has half the house without power", short="Half the house is dark.", search="search for an electrician", on_job="up a ladder",
                      job_stat="$4,000", job_label="full panel replacement", job_spoken="a four thousand dollar electrical panel replacement", job_short="four thousand dollar panel replacement", price=4000),
 "roofing":      dict(emergency="has rain coming through the roof", short="There's rain coming through their roof.", search="search for a roofer", on_job="up on a roof",
                      job_stat="$30,000", job_label="full roof replacement", job_spoken="a thirty thousand dollar roof replacement", job_short="thirty thousand dollar roof replacement", price=30000),
 "water_damage": dict(emergency="has sewage backing up into the basement", short="Sewage is backing up into their basement.", search="search for a water damage restoration company", on_job="in the middle of someone else's emergency",
                      job_stat="$100,000", job_label="Category 3 water loss job", job_spoken="a hundred thousand dollar Category 3 water loss job", job_short="Category 3 water loss job", price=100000),
 "garage_door":  dict(emergency="has a garage door that just came off its tracks", short="Their garage door is off its tracks and won't move.", search="search for a garage door repair company", on_job="on a ladder in a garage",
                      job_stat="$4,000", job_label="full garage door replacement", job_spoken="a four thousand dollar garage door replacement", job_short="four thousand dollar garage door replacement", price=4000),
}
WORD = {1: "a year", 2: "two years", 3: "three years", 4: "four years", 5: "five years", 6: "six years", 7: "seven years", 8: "eight years", 9: "nine years"}

def payback(price):
    """Months of founder-priced service ($497 first month, $247 after) that one job covers, expressed conservatively."""
    cost = lambda m: 497 + (m - 1) * 247
    months = 1
    while cost(months + 1) <= price: months += 1
    years = months // 12
    if years >= 10: return "more than a decade", 120, cost(120)
    return "more than " + WORD[max(years, 1)], max(years, 1) * 12, cost(max(years, 1) * 12)

def slides(n, biz):
    pb, m, c = payback(n["price"])
    S = []
    S.append(dict(type="title", title="It's 9 PM. The *phone rings*. *Nobody answers.*", sub="What one unanswered call can cost a home service company",
      narration=f"Picture this. It's nine o'clock at night, and a homeowner {n['emergency']}. They grab their phone, {n['search']}, and call the first name they see. It rings. And rings. Nobody picks up. They're not going to leave a voicemail. {n['short']} So they hang up, and call the next company on the list. And you'd never even know it happened."))
    S.append(dict(type="stat", big=n["job_stat"], label=f"a *{n['job_label']}*, on the other end of one unanswered call",
      note="Example of a large job. Actual job values and outcomes vary.", transition="fade",
      narration=f"Here's what makes that so painful. That call wasn't a two hundred dollar service visit. For a company like yours, it could have been {n['job_spoken']}. And the big jobs don't wait for business hours. They show up at the worst possible time, from people who need an answer right now."))
    S.append(dict(type="stat", big="~38%", label="of calls go *unanswered*, even at businesses that list *24/7 hours*",
      note="Approximate. Based on what OnCall Local has found in its own after-hours calls to home service businesses that list 24/7 hours.",
      narration="Now, you might think a twenty-four seven business has this covered. Here's what we've found. Among home service businesses that list their hours as twenty-four seven, approximately thirty-eight percent of calls go unanswered. And that's not because those owners don't care. It's because everyone misses calls. Period."))
    S.append(dict(type="cols", title="Why calls get missed",
      cards=[{"h":"On the job","p":"Hands full, phone in the truck."},{"h":"After hours","p":"Dinner, family time, or asleep at two in the morning."},{"h":"Even with a team","p":"Staffed phones still miss calls."}],
      narration=f"Think about your day. You're {n['on_job']}, or in the middle of a job with another customer. Or you're finally sitting down to dinner. Even companies with a team answering the phones around the clock still miss calls. Nobody can pick up every single one. So let's look at what actually happens when a call gets missed."))
    S.append(dict(type="clip", clip="__BEFORE__", transition="smoothleft", note="Illustration only. Not a real customer or call.",
      narration="Here's the customer's side of it. They search. They find you. They tap call. It rings, and nobody answers. So they go back to the list, tap the next company, and that company picks up. Just like that, the job is gone, before you ever knew it existed."))
    S.append(dict(type="clip", clip="__AFTER__", transition="fade", note="Illustration only. Not a real customer or call.",
      narration="Now watch the same moment with missed call text back. They tap call. Nobody answers. But right before they tap the next company, a text pops up from your business. Sorry we missed your call, how can we help? The conversation has started, and it started with you."))
    S.append(dict(type="stat", big="$83K+", label="in *sold jobs* this year for *one of our clients*", transition="fadeblack",
      note="One current OnCall Local client in Northern California. $83,000+ in sold jobs this year, per the client's records. One client's result. Results vary and are not guaranteed; they depend on call volume, response speed, pricing and follow-up.",
      narration="And this isn't theory. One of our clients, in Northern California, already has their own employees answering the phones twenty-four seven, three sixty-five. And still, calls slipped through. With missed call text back running behind their team, they've sold over eighty-three thousand dollars in jobs this year. Work that might have gone to the next company on the list."))
    S.append(dict(type="bullets", title="How *missed call text back* works",
      items=["A call goes *unanswered*","The caller gets a *text from your business* in seconds","An *assistant* finds out who they are and what they need","You get the *whole conversation*, and you *call back first*"],
      note="The text assistant is an AI and introduces itself as your business's virtual assistant.",
      narration="So how does it work? When a call goes unanswered, the caller gets a text from your business within seconds. A virtual assistant asks what's going on and gets the details. Then you get the whole conversation on your phone, and you call them back first."))
    S.append(dict(type="quote", text="You don't have to answer *every* call. You just have to be the *first to respond*.",
      narration="And that's really the whole idea. These customers aren't waiting around. They're shopping, right now. A text starts the conversation while they're still deciding who to hire. You don't have to answer every call. You just have to be the first to respond."))
    S.append(dict(type="cols", title="What you need to do",
      cards=[{"h":"We build it","p":"Everything is set up in your account for you."},{"h":"Keep your number","p":"Your calls forward after a few rings if you don't pick up."},{"h":"You call back","p":"Read the conversation, then call the customer."}],
      narration="The best part is, there's nothing for you to build. We set everything up inside your account. You keep your own phone number. If you don't pick up after a few rings, the call forwards, and the text goes out. All you do is read the conversation, and call them back."))
    S.append(dict(type="bullets", title="Founder pricing", items=["*$497* for your first month","Then *$247* a month","*No contract*, cancel anytime"],
      note="Founder pricing: $497 first month (includes setup), then $247/month. Pricing may change for future customers.",
      narration="So what does it cost? Right now, we're offering founder pricing. Four hundred ninety-seven dollars for your first month, then two hundred forty-seven dollars a month after that. No contract, and you can cancel anytime."))
    S.append(dict(type="stat", big="1 job", label=f"can cover *{pb}* of service",
      note=f"Illustration only. Founder pricing for {m} months totals ${c:,} ($497 + {m-1} x $247); a {n['job_stat']} job exceeds that. Results are not guaranteed.",
      narration=f"And think about the math for a second. One {n['job_short']} covers {pb} of service. And the call that starts it could be the one you miss tonight."))
    S.append(dict(type="title", title="Reply to the email and *say you're in*", sub="Or reply with any questions. We'll get you set up.", transition="fadeblack",
      narration="If this sounds like something you'd want working for you, just reply to the email and say you're in. Or, if you have any questions, just reply with those. We'll take it from there. Thanks for watching."))
    return S

QUERY_NICHE = {"plumber": "plumber", "hvac contractor": "hvac", "electrician": "electrician", "roofing contractor": "roofing",
               "water damage restoration": "water_damage", "garage door repair": "garage_door"}

def from_lead(phone, csv_path):
    """Real lead data from the scrape CSV, plus the real call day/time from GHL when it exists."""
    sys.path.insert(0, ROOT)
    from mce import scrape
    row = next((r for r in scrape.read_csv(csv_path) if r["phone"] == phone), None)
    if not row: sys.exit(f"{phone} not found in {csv_path}")
    niche = QUERY_NICHE.get(row["query"].split(" in ")[0].strip().lower())
    if not niche: sys.exit(f"no video template for trade '{row['query']}'")
    info = dict(niche=niche, biz=row["name"], rating=row["rating"], reviews=row["reviews"], hours=row["hours"] or ("Open 24 hours" if row["is_24_7"] else ""),
                email=row.get("email", ""), website=row.get("website", ""), call_day=None, call_time=None)
    try:
        from mce import ghl
        c = ghl.find_by_phone(phone)
        if c:
            f = ghl.field_values(ghl.call("GET", f"/contacts/{c[0]['id']}")["contact"]); info["call_day"], info["call_time"] = f.get("call_day"), f.get("call_time")
    except Exception as e: print("note: could not read the call time from GHL:", str(e)[:100])
    return info

def from_contact(contact_id):
    """Real lead data straight from GHL (no local CSV needed): name, trade, rating, reviews, hours, email, call day/time."""
    sys.path.insert(0, ROOT)
    from mce import ghl
    c = ghl.call("GET", f"/contacts/{contact_id}")["contact"]; f = ghl.field_values(c)
    niche = QUERY_NICHE.get((f.get("source_query") or "").split(" in ")[0].strip().lower())
    if not niche: sys.exit(f"no video template for trade '{f.get('source_query')}'")
    tags = {t.lower() for t in c.get("tags", [])}
    return dict(niche=niche, biz=c.get("companyName") or c.get("contactName"), rating=f.get("rating"), reviews=f.get("reviews"),
                hours="Open 24 hours" if "mce-24-7" in tags else "", email=c.get("email") or "", website=c.get("website") or "",
                call_day=f.get("call_day"), call_time=f.get("call_time"))

def merged_emails(info, niche):
    """Email 1 and Email 2 with this lead's real data merged in. Preview only; nothing is sent."""
    sys.path.insert(0, ROOT)
    from mce.config import BIG_JOB
    key = next(q for q, k in QUERY_NICHE.items() if k == niche)
    job = BIG_JOB[key]; day, tm = info["call_day"] or "[DAY]", info["call_time"] or "[TIME]"
    e1 = f"""Subject: No one picked up at {tm}

Hi there,

We called {info['biz']} {day} night at {tm} as part of an after-hours phone audit we're running for local service companies. Nobody picked up.

I'm not writing to scold you. I'm writing because of what that call could have been.

If that had been a real customer, ready to book {job}, they wouldn't have waited for a callback. They would have hung up and called the next company on Google. And you would never have known the call happened.

That's the part that stings: it isn't the one call, it's that the biggest jobs often come in at the worst times, from people who need an answer right now.

There's a simple fix, and it costs far less than a single job. The moment a call goes unanswered, the caller gets a text from your business. An assistant finds out who they are and what they need, and the whole conversation lands on your phone so you can call them back first.

Would you mind if I sent you a short video (under 5 minutes) showing exactly how it works? Just reply "yes" and I'll send it over.

Sam
OnCall Local
"""
    e2 = """Subject: Your video: what a missed call really costs

Thanks for saying yes. Here's the video (under 5 minutes):

[VIDEO LINK]

It covers what an unanswered after-hours call can cost, how the text-back works, and founder pricing: $497 for the first month, then $247 a month, no contract.

If it makes sense, just reply to this email and I'll get you set up. If you have questions, reply with those instead.

Sam
OnCall Local
"""
    return e1 + "\n---\n\n" + e2

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--niche", choices=sorted(NICHES)); ap.add_argument("--biz"); ap.add_argument("--slug")
    ap.add_argument("--phone", help="build from a real lead: its E.164 phone in the CSV"); ap.add_argument("--contact", help="build from a GHL contact id (no CSV needed)"); ap.add_argument("--csv", default="data/tampa_batch1.csv")
    ap.add_argument("--rating"); ap.add_argument("--reviews"); ap.add_argument("--hours"); ap.add_argument("--skip-render", action="store_true"); ap.add_argument("--md")
    a = ap.parse_args(); info = None
    if a.contact:
        info = from_contact(a.contact); a.niche = a.niche or info["niche"]; a.biz = a.biz or info["biz"]; a.rating = a.rating or info["rating"]; a.reviews = a.reviews or info["reviews"]; a.hours = a.hours if a.hours is not None else info["hours"]
        a.slug = a.slug or "".join(ch if ch.isalnum() else "_" for ch in a.biz.lower()).strip("_")
    elif a.phone:
        info = from_lead(a.phone, a.csv); a.niche = a.niche or info["niche"]; a.biz = a.biz or info["biz"]; a.rating = a.rating or info["rating"]; a.reviews = a.reviews or info["reviews"]; a.hours = a.hours if a.hours is not None else info["hours"]
        a.slug = a.slug or "".join(ch if ch.isalnum() else "_" for ch in a.biz.lower()).strip("_")
    if not (a.niche and a.biz and a.slug): ap.error("give --contact or --phone, or all of --niche --biz --slug")
    n = NICHES[a.niche]
    os.makedirs(f"{ROOT}/lessons/gen", exist_ok=True); os.makedirs(f"{ROOT}/lessons/clips/gen", exist_ok=True)
    before, after = f"clips/gen/{a.slug}_before.mp4", f"clips/gen/{a.slug}_after.mp4"
    if not a.skip_render:
        procs = [subprocess.Popen(["node", f"{ROOT}/tools/render_anim.js", mode, f"{ROOT}/lessons/{path}", "--niche", a.niche, "--biz", a.biz] + [x for k, v in (("--rating", a.rating), ("--reviews", a.reviews), ("--hours", a.hours)) for x in ((k, str(v)) if v not in (None, "", 0) else ())])
                 for mode, path in (("before", before), ("after", after))]
        if any(p.wait() for p in procs): sys.exit("animation render failed")
    S = slides(n, a.biz)
    for s in S:
        if s.get("clip") == "__BEFORE__": s["clip"] = before
        if s.get("clip") == "__AFTER__": s["clip"] = after
    lesson = {"id": "9.0", "out": a.slug, "title": "Missed Call Text Back: video sales letter", "footer": "OnCall Local", "slides": S}
    path = f"{ROOT}/lessons/gen/{a.slug}.json"; json.dump(lesson, open(path, "w"), indent=1)
    words = sum(len(s["narration"].split()) for s in S); print(f"{a.slug}: {len(S)} slides, {words} words")
    if a.md:
        open(a.md, "w").write(f"# Script: {a.niche} / {a.biz}\n\n" + "\n\n".join(f"**{i+1}.** {s['narration']}" for i, s in enumerate(S)) + "\n")
    if info:
        e = f"{ROOT}/lessons/gen/{a.slug}_emails.md"; open(e, "w").write(f"# Preview only. Not sent.\n\nTo: {info['email'] or '(no email found)'}\nCall: {info['call_day']} {info['call_time']}\n\n" + merged_emails(info, a.niche)); print("email preview:", e)
    if not os.environ.get("VSL_NO_BUILD"):
        subprocess.check_call(["node", f"{ROOT}/pipeline/build.js", path])

if __name__ == "__main__": main()
