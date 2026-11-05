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


# ---------- deeper search: JavaScript-rendered pages, protected addresses, structured data ----------
import json as _json, binascii
from urllib.parse import urlparse
from .config import bee_key

PERSONAL = ("gmail.com", "yahoo.com", "aol.com", "outlook.com", "hotmail.com", "icloud.com", "msn.com", "live.com")

def _rendered(url):
    """Fetch a page through ScrapingBee with JavaScript rendered (5 credits)."""
    try:
        r = requests.get("https://app.scrapingbee.com/api/v1/", timeout=90, params={"api_key": bee_key(), "url": url, "render_js": "true", "wait": "2500"})
        return r.text if r.ok else ""
    except Exception:
        return ""

def _decode_cf(hexstr):
    try:
        b = binascii.unhexlify(hexstr); k = b[0]; return "".join(chr(x ^ k) for x in b[1:])
    except Exception:
        return ""

def emails_in(html):
    out = []
    for m in re.findall(r'data-cfemail="([0-9a-f]+)"', html): out.append(_decode_cf(m))
    out += re.findall(r"mailto:([^\"'?>\s]+)", html)
    for blob in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S):
        out += re.findall(r'"email"\s*:\s*"([^"]+)"', blob)
    out += EMAIL.findall(html)
    seen, res = set(), []
    for e in out:
        e = e.strip().lower().rstrip(".").replace("mailto:", "")
        if EMAIL.fullmatch(e) and not JUNK.search(e) and e not in seen: seen.add(e); res.append(e)
    return res

def find_email_deep(site):
    """Returns (email, where_found) or ('', ''). Prefers the company's own domain, then a personal address, then anything else."""
    if not site: return "", ""
    root = site if site.startswith("http") else "https://" + site
    host = urlparse(root).netloc.lower().removeprefix("www.")
    found = []
    for path in ("", "contact", "contact-us", "about", "about-us"):
        url = urljoin(root if path == "" else root.rstrip("/") + "/", path)
        for e in emails_in(_rendered(url)):
            if e not in [x[0] for x in found]: found.append((e, url))
        if len(found) >= 3: break
    if not found: return "", ""
    own = [f for f in found if f[0].split("@")[1].removeprefix("www.").endswith(host.split(".")[-2] + "." + host.split(".")[-1])]
    personal = [f for f in found if f[0].split("@")[1] in PERSONAL]
    pool = own or personal or found
    pool.sort(key=lambda f: next((i for i, p in enumerate(PREFER) if f[0].startswith(p)), 99))
    return pool[0]
