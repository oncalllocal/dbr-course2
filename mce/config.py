import os, sys

def need(name):
    v = os.environ.get(name)
    if not v:
        sys.exit(f"Missing env var {name}")
    return v

def ghl_token():      return need("GHL_TOKEN")
def ghl_location():   return need("GHL_LOCATION_ID")
def bee_key():        return need("SCRAPINGBEE_API_KEY")

GHL_BASE = "https://services.leadconnectorhq.com"
GHL_VERSION = "2021-07-28"

# Tags this system owns. GHL lowercases tags, so keep these lowercase.
TAG_PROSPECT  = "mce-prospect"
TAG_QUEUE     = "mce-dial-queue"   # adding this tag starts the call workflow
TAG_ANSWERED  = "mce-answered"
TAG_NOANSWER  = "mce-no-answer"
TAG_24_7      = "mce-24-7"

# Existing custom fields in the sub-account (looked up by fieldKey at runtime).
FIELD_KEYS = {
    "big_job":      "contact.mctb_big_job",
    "score":        "contact.mctb_lead_score",
    "source_query": "contact.audit_source_query",
    "reviews":      "contact.audit_maps_reviews",
    "rating":       "contact.audit_maps_rating",
    "trade":        "contact.audit_trade",
    "outcome":      "contact.audit_outcome",
    "call_day":     "contact.audit_call_day",
    "call_time":    "contact.audit_call_time",
}

TAG_CELL_MANUAL = "mce-cell-manual"   # mobile numbers: never auto-dialed, called by hand
TAG_LINE = {"mobile": "mce-line-mobile", "landline": "mce-line-landline", "voip": "mce-line-voip",
            "tollfree": "mce-line-tollfree", "unknown": "mce-line-unknown"}
PIPELINE_NAME = "Missed Call Prospects"
STAGE_MANUAL = "Manual Call - Cell"
STAGE_DNA = "Did not answer"
TAG_MANUAL_TASKED = "mce-manual-tasked"
MIN_SCORE = 25
MANUAL_PER_DAY = 20

# What a missed after-hours call could have been, by trade (owner-approved, 2026-11-04). Used in the first email.
BIG_JOB = {
    "plumber": "a $12,000 whole-home repipe",
    "hvac contractor": "a $15,000 system replacement",
    "electrician": "a $4,000 full panel replacement",
    "roofing contractor": "a $30,000 full roof replacement",
    "water damage restoration": "a $100,000 Category 3 water loss job",
    "garage door repair": "a $4,000 full garage door replacement",
}
def big_job_for(query):
    """query looks like 'plumber in Tampa FL'."""
    return BIG_JOB.get((query or "").split(" in ")[0].strip().lower(), "")
