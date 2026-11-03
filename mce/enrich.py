"""Find a public contact email on each lead's own website (homepage + contact page)."""
import re, requests
from urllib.parse import urljoin

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
JUNK = re.compile(r"(example\.|sentry|wixpress|godaddy|squarespace|\.png|\.jpg|\.gif|\.webp|\.svg|@2x|schema\.org|domain\.com|email\.com|yourname|name@)", re.I)
PREFER = ("info", "contact", "office", "service", "hello", "support", "sales", "admin")
UA = {"User-Agent": "Mozilla/5.0 (compatible; OnCallLocalBot/1.0)"}

def _get(url):
    try:
        r = requests.get(url, headers=UA, timeout=12, allow_redirects=True)
        return r.text if r.ok and "text" in r.headers.get("content-type", "text") else ""
    except Exception:
        return ""

def find_email(site):
    if not site: return ""
    found = []
    pages = [site] + [urljoin(site, p) for p in ("contact", "contact-us", "about")]
    for u in pages:
        html = _get(u)
        for m in re.findall(r"mailto:([^\"'?>\s]+)", html) + EMAIL.findall(html):
            m = m.strip().lower().rstrip(".")
            if EMAIL.fullmatch(m) and not JUNK.search(m) and m not in found: found.append(m)
        if found: break
    if not found: return ""
    domain = re.sub(r"^https?://(www\.)?", "", site).split("/")[0]
    same = [e for e in found if e.split("@")[1].endswith(domain.split(".")[-2] + "." + domain.split(".")[-1])] or found
    same.sort(key=lambda e: next((i for i, p in enumerate(PREFER) if e.startswith(p)), 99))
    return same[0]

def enrich_all(leads):
    n = 0
    for l in leads:
        if not l.get("email"):
            l["email"] = find_email(l.get("website"))
            n += bool(l["email"])
    return n
