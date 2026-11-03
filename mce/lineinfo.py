"""Phone line-type screening: mobile / landline / voip / tollfree / unknown.

Toll-free is detected offline. Everything else needs a lookup provider; set
TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN to use Twilio Lookup v2 (line_type_intelligence).
Results are cached in data/line_cache.json so each number is only looked up once.
"""
import os, json, requests

TOLL_FREE = {"800", "833", "844", "855", "866", "877", "888"}
CACHE_PATH = "data/line_cache.json"
TWILIO_MAP = {"mobile": "mobile", "landline": "landline", "fixedVoip": "voip",
              "nonFixedVoip": "voip", "tollFree": "tollfree", "voip": "voip"}

def _cache():
    try: return json.load(open(CACHE_PATH))
    except Exception: return {}

def _save(c):
    os.makedirs("data", exist_ok=True); json.dump(c, open(CACHE_PATH, "w"), indent=1)

def provider():
    return "twilio" if os.environ.get("TWILIO_ACCOUNT_SID") and os.environ.get("TWILIO_AUTH_TOKEN") else None

def _twilio(phone):
    r = requests.get(f"https://lookups.twilio.com/v2/PhoneNumbers/{phone}",
                     params={"Fields": "line_type_intelligence"}, timeout=30,
                     auth=(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"]))
    if r.status_code != 200:
        raise RuntimeError(f"Twilio Lookup {r.status_code}: {r.text[:200]}")
    t = (r.json().get("line_type_intelligence") or {}).get("type")
    return TWILIO_MAP.get(t, "unknown")

def classify(phone, cache):
    if not phone: return "unknown"
    if phone[2:5] in TOLL_FREE: return "tollfree"
    if phone in cache: return cache[phone]
    if provider() == "twilio":
        cache[phone] = _twilio(phone); return cache[phone]
    return "unknown"          # no provider configured: not cached, so a later lookup still runs

def classify_all(leads):
    cache = _cache()
    for l in leads:
        l["line_type"] = classify(l["phone"], cache)
    _save(cache)
    return leads
