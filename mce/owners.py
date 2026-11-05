"""Owner research (read-only pilot): who runs this business, and where did we see it?

Sources: the company's own About/Team pages, the Florida business registry (Sunbiz, public record), and the company's Facebook page.
Everything returned carries its source and evidence so a person can judge it. Nothing is written to GHL by this module.
"""
import os, re, json, html as H
from urllib.parse import quote, urljoin
import requests
from .config import bee_key
from .enrich import emails_in

BAY = {"tampa","brandon","riverview","seffner","valrico","plant city","lutz","land o lakes","wesley chapel","odessa","oldsmar","temple terrace","ruskin","apollo beach","sun city center","st petersburg","saint petersburg","clearwater","largo","pinellas park","dunedin","safety harbor","zephyrhills","dover","thonotosassa","lithia","gibsonton","wimauma","new port richey","palm harbor","seminole","bradenton"}
STOP = {"our team","learn more","contact us","about us","read more","free estimate","get started","call now","meet the","family owned","locally owned","licensed insured","years experience","customer service","pro team"}

def bee(url, **kw):
    p = {"api_key": bee_key(), "url": url, **kw}
    try:
        r = requests.get("https://app.scrapingbee.com/api/v1/", params=p, timeout=120); return r.text if r.ok else ""
    except Exception: return ""

def text_of(html):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html or "", flags=re.S | re.I); t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", H.unescape(t))

NAME = r"([A-Z][a-z]{1,15}(?:\s+[A-Z]\.?)?\s+[A-Z][a-zA-Z'\-]{1,20})"
TITLE = r"(?:owner|co-owner|founder|co-founder|president|ceo|general manager|master (?:plumber|electrician)|managing member)"
PATTERNS = [re.compile(NAME + r"\s*[,\-\u2013\u2014|:(]+\s*" + TITLE, re.I), re.compile(TITLE + r"[,\s:\-\u2013\u2014]+" + NAME, re.I),
            re.compile(r"(?:owned|founded|started|operated|run) by\s+" + NAME, re.I), re.compile(r"(?:meet|hi,? i'?m|my name is|i'?m)\s+" + NAME, re.I)]

def owner_candidates(text):
    out = []
    for rx in PATTERNS:
        for m in rx.finditer(text):
            n = m.group(1).strip()
            if n.lower() in STOP or any(s in n.lower() for s in STOP) or len(n.split()) < 2: continue
            if re.search(r"\b(Tampa|Florida|Bay|Roofing|Plumbing|Electric|Air|Services|Company|Home|Repair|Door)\b", n): continue
            snip = text[max(0, m.start() - 40): m.end() + 40]
            if n not in [x[0] for x in out]: out.append((n, snip))
    return out[:3]

def about_pass(site):
    res = {"names": [], "emails": []}
    if not site: return res
    root = site if site.startswith("http") else "https://" + site
    for path in ("", "about", "about-us", "our-team", "team", "meet-the-team", "our-story", "contact"):
        h = bee(urljoin(root if path == "" else root.rstrip("/") + "/", path), render_js="true", wait="2000")
        if not h: continue
        res["emails"] += [e for e in emails_in(h) if e not in res["emails"]]
        for n, sn in owner_candidates(text_of(h)):
            if n not in [x["name"] for x in res["names"]]: res["names"].append({"name": n, "source": f"website /{path}", "evidence": sn})
        if len(res["names"]) >= 2 and len(res["emails"]) >= 1: break
    return res

def norm(s): return re.sub(r"\b(llc|l l c|inc|corp|co|company|the|corporation|incorporated)\b", "", re.sub(r"[^a-z0-9 ]", " ", s.lower())).split().__str__()

def sunbiz(name, street=""):
    q = re.sub(r"\s+(LLC|Inc\.?|Corp\.?)$", "", name, flags=re.I)
    h = bee(f"https://search.sunbiz.org/Inquiry/CorporationSearch/SearchResults?inquiryType=EntityName&searchNameOrder={quote(q.upper())}&searchTerm={quote(q)}")
    rows = re.findall(r'href="(/Inquiry/CorporationSearch/SearchResultDetail[^"]+)"[^>]*>([^<]+)</a>', h)
    cand = [(u, H.unescape(n).strip()) for u, n in rows if norm(H.unescape(n)) == norm(q) or norm(H.unescape(n)).startswith(norm(q)[:-1])][:3]
    found = []
    for u, n in cand:
        d = bee("https://search.sunbiz.org" + u.replace("&amp;", "&")); t = text_of(d)
        city = (re.search(r"Principal Address[^A-Z]*.*?([A-Z][A-Za-z .]+),\s*FL", t) or [None, ""])[1].strip().lower()
        addr = t[t.find("Principal Address"): t.find("Principal Address") + 160] if "Principal Address" in t else ""
        people = re.findall(r"Title\s*([A-Z/ ]{2,12})\s+([A-Z][A-Z' .\-]+,\s*[A-Z][A-Z' .\-]+?)\s+\d", t)
        names = [{"name": " ".join(p.split(",")[::-1]).strip().title(), "title": ti.strip()} for ti, p in people]
        street_ok = bool(street) and street.split()[0] in addr
        found.append({"entity": n, "people": names[:4], "bay_area": city in BAY or any(b in addr.lower() for b in BAY), "street_match": street_ok, "principal": addr[:120]})
    return found

def facebook(name):
    h = bee("https://www.google.com/search?q=" + quote(f'"{name}" Tampa facebook'), custom_google="true")
    m = re.search(r'https://(?:www\.)?facebook\.com/[A-Za-z0-9.\-_/]+', h or "")
    if not m: return {}
    url = m.group(0).split("?")[0].rstrip("/")
    page = bee(url + "/about", render_js="true", premium_proxy="true", wait="3000")
    return {"url": url, "emails": emails_in(page), "text_sample": text_of(page)[:300]} if page else {"url": url}

def research(contact):
    name = contact.get("companyName") or contact.get("contactName"); site = contact.get("website"); street = (contact.get("address1") or "")
    out = {"name": name, "site": site, "email_on_file": contact.get("email")}
    out["about"] = about_pass(site); out["sunbiz"] = sunbiz(name, street)
    try: out["facebook"] = facebook(name)
    except Exception as e: out["facebook"] = {"error": str(e)[:80]}
    return out
