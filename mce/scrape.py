"""Google Maps lead scraper (via ScrapingBee) + scoring."""
import re, json, csv, time
from html import unescape
from urllib.parse import quote_plus
import requests
from .config import bee_key

# National brands with corporate call centers: they will always answer, so skip by default.
FRANCHISE_HINTS = [
    "roto-rooter", "mr. rooter", "mr rooter", "benjamin franklin", "one hour", "aire serv",
    "mister sparky", "mr. electric", "mr electric", "ars rescue", "service experts", "lennox",
    "trane", "carrier", "home depot", "lowe's", "sears", "american standard", "terminix",
    "orkin", "aptive", "rentokil", "rainbow", "service champions", "len the plumber",
]
H24_HINTS = re.compile(r"24\s*/?\s*7|24[- ]?hour|24[- ]?hr|emergency|all hours|anytime|around the clock", re.I)

def fetch_html(query, scrolls=6):
    url = f"https://www.google.com/maps/search/{quote_plus(query)}?hl=en"
    scroll = "(()=>{const f=document.querySelector('div[role=feed]');if(f)f.scrollBy(0,6000);window.scrollBy(0,3000)})()"
    steps = [{"wait": 3000}]
    for _ in range(scrolls):
        steps += [{"evaluate": scroll}, {"wait": 1800}]
    r = requests.get("https://app.scrapingbee.com/api/v1/", timeout=180, params={
        "api_key": bee_key(), "url": url, "custom_google": "true", "render_js": "true",
        "country_code": "us", "js_scenario": json.dumps({"instructions": steps}),
    })
    r.raise_for_status()
    return r.text

def to_e164(raw):
    d = re.sub(r"\D", "", raw or "")
    if len(d) == 11 and d[0] == "1": d = d[1:]
    return "+1" + d if len(d) == 10 else None

def parse(html, query):
    out = []
    for c in html.split('class="Nv2PK')[1:]:
        c = c.split('class="Nv2PK')[0]
        text = re.sub(r"<[^>]+>", "|", c)
        text = re.sub(r"\|+", "|", unescape(text))
        name = re.search(r'aria-label="([^"]+)"[^>]*href="https://www\.google\.com/maps/place', c)
        phone = re.search(r"\(\d{3}\) \d{3}-\d{4}", text)
        rv = re.search(r"(\d\.\d)\|\(([\d,]+)\)", text)
        pid = re.search(r"!1s(0x[0-9a-f]+:0x[0-9a-f]+)", c)
        sites = [u for u in re.findall(r'href="(https?://[^"]+)"', c)
                 if "google." not in u and "servicetitan" not in u and "booksy" not in u]
        if not (name and phone): continue
        parts = [p.strip(" ·") for p in text.split("|") if p.strip(" ·")]
        cat = parts[parts.index(f"({rv.group(2)})") + 1] if rv and f"({rv.group(2)})" in parts else ""
        addr = next((p for p in parts if re.match(r"^\d+ \w", p)), "")
        hours = ""
        m = re.search(r"(Open 24 hours|Open ?\|? ?·? ?Closes[^|]*|Closed[^|]*|Opens[^|]*)", text)
        if m: hours = re.sub(r"\s+", " ", m.group(1).replace("|", " ")).strip(" ·")
        out.append({
            "place_id": pid.group(1) if pid else "",
            "name": unescape(name.group(1)),
            "phone": to_e164(phone.group(0)),
            "category": cat, "address": addr,
            "rating": float(rv.group(1)) if rv else None,
            "reviews": int(rv.group(2).replace(",", "")) if rv else 0,
            "website": sites[0].split("?")[0] if sites else "",
            "hours": hours, "open_24": "Open 24 hours" in text,
            "query": query,
        })
    return out

def score(l, keep_franchises=False):
    n = l["name"].lower()
    if not keep_franchises and any(h in n for h in FRANCHISE_HINTS):
        return None
    s = 0
    l["is_24_7"] = bool(l["open_24"] or H24_HINTS.search(l["name"]))
    if l["is_24_7"]: s += 40          # losing the most per missed call
    r = l["reviews"]
    s += 25 if r < 50 else 20 if r < 150 else 10 if r < 400 else 0 if r < 1000 else -10
    if l["website"]: s += 5           # we can pull info to train the demo bot
    if (l["rating"] or 0) >= 4.0: s += 5
    return s

def run(queries, scrolls=6, keep_franchises=False):
    seen, leads = set(), []
    for q in queries:
        for l in parse(fetch_html(q, scrolls), q):
            key = l["phone"]
            if not key or key in seen: continue
            seen.add(key)
            s = score(l, keep_franchises)
            if s is None: continue
            l["score"] = s
            leads.append(l)
        time.sleep(1)
    return sorted(leads, key=lambda x: -x["score"])

FIELDS = ["score","name","phone","category","address","rating","reviews","website","hours","is_24_7","place_id","query"]
def write_csv(leads, path):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, FIELDS, extrasaction="ignore"); w.writeheader(); w.writerows(leads)

def read_csv(path):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["reviews"] = int(r["reviews"] or 0); r["is_24_7"] = r["is_24_7"] == "True"
    return rows
