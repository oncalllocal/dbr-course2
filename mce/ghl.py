"""Thin GoHighLevel API client for the prospecting sub-account."""
import time, requests
from .config import *

def _h():
    return {"Authorization": f"Bearer {ghl_token()}", "Version": GHL_VERSION,
            "Accept": "application/json", "Content-Type": "application/json"}

def call(method, path, **kw):
    for attempt in range(5):
        r = requests.request(method, GHL_BASE + path, headers=_h(), timeout=60, **kw)
        if r.status_code == 429:
            time.sleep(2 ** attempt); continue
        if r.status_code >= 400:
            raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text[:300]}")
        return r.json() if r.text else {}
    raise RuntimeError("rate limited")

_field_ids = None
def field_ids():
    global _field_ids
    if _field_ids is None:
        fs = call("GET", f"/locations/{ghl_location()}/customFields")["customFields"]
        by_key = {f["fieldKey"]: f["id"] for f in fs}
        _field_ids = {k: by_key.get(v) for k, v in FIELD_KEYS.items()}
    return _field_ids

def upsert_lead(l, extra_tags=()):
    ids = field_ids()
    vals = {"source_query": l["query"], "reviews": l["reviews"], "rating": l["rating"],
            "trade": l.get("trade") or l["category"]}
    tags = [TAG_PROSPECT, *extra_tags]
    lt = l.get("line_type") or "unknown"
    tags.append(TAG_LINE.get(lt, TAG_LINE["unknown"]))
    if lt == "mobile": tags.append(TAG_CELL_MANUAL)
    if l["is_24_7"]: tags.append(TAG_24_7)
    body = {
        "locationId": ghl_location(), "name": l["name"], "companyName": l["name"],
        "phone": l["phone"], "email": l.get("email") or None, "website": l["website"] or None, "address1": l["address"] or None,
        "source": "mce-maps-scrape", "tags": tags,
        "customFields": [{"id": ids[k], "field_value": str(v)} for k, v in vals.items()
                         if ids.get(k) and v not in (None, "")],
    }
    res = call("POST", "/contacts/upsert", json=body)
    return res["contact"]["id"], res.get("new", None)

def add_tags(contact_id, tags):
    return call("POST", f"/contacts/{contact_id}/tags", json={"tags": list(tags)})

def find_by_phone(phone):
    res = call("GET", "/contacts/", params={"locationId": ghl_location(), "query": phone, "limit": 5})
    return res.get("contacts", [])

def list_contacts(tag=None, limit=100):
    out, params = [], {"locationId": ghl_location(), "limit": limit}
    while True:
        res = call("GET", "/contacts/", params=params)
        out += res.get("contacts", [])
        nxt = res.get("meta", {}).get("startAfterId")
        if not nxt or not res.get("contacts"): break
        params.update(startAfterId=nxt, startAfter=res["meta"]["startAfter"])
    return [c for c in out if not tag or tag in [t.lower() for t in c.get("tags", [])]]


def add_task(contact_id, title, body, due_iso):
    return call("POST", f"/contacts/{contact_id}/tasks",
                json={"title": title, "body": body, "dueDate": due_iso, "completed": False})

_pipes = None
def pipeline_stage(pipeline_name, stage_name):
    """Return (pipeline_id, stage_id) or None. Pipelines must be created by hand in the GHL UI."""
    global _pipes
    if _pipes is None:
        _pipes = call("GET", "/opportunities/pipelines", params={"locationId": ghl_location()})["pipelines"]
    for p in _pipes:
        if p["name"].lower() == pipeline_name.lower():
            for st in p["stages"]:
                if st["name"].lower() == stage_name.lower():
                    return p["id"], st["id"]
    return None

def add_opportunity(contact_id, name, pipeline_id, stage_id):
    return call("POST", "/opportunities/", json={"locationId": ghl_location(), "name": name,
                "pipelineId": pipeline_id, "pipelineStageId": stage_id,
                "contactId": contact_id, "status": "open"})
