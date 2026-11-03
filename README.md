# Missed Call Engine

Lead sourcing and prospecting pipeline for a GHL missed-call-text-back offer.

```
python3 -m mce scrape --trades "plumber,hvac contractor" --cities "Tampa FL" --out data/leads.csv
python3 -m mce push data/leads.csv --limit 50 --dry-run     # preview
python3 -m mce push data/leads.csv --limit 50               # import to GHL (no calls)
python3 -m mce push data/leads.csv --limit 50 --queue       # import AND start the call workflow
python3 -m mce results                                      # export answered / no-answer
```

Env vars: `GHL_TOKEN`, `GHL_LOCATION_ID`, `SCRAPINGBEE_API_KEY`.
Workflow setup: `docs/ghl-dialer-workflow.md`.
