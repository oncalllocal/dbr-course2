# Missed Call Engine

Lead sourcing and prospecting pipeline for a GHL missed-call-text-back offer.

```
python3 -m mce scrape --trades "plumber,hvac contractor" --cities "Tampa FL" --out data/leads.csv
python3 -m mce lookup data/leads.csv                         # classify mobile/landline/voip/tollfree (needs TWILIO_* env)
python3 -m mce enrich data/leads.csv                         # find public emails on lead websites
python3 -m mce push data/leads.csv --limit 50 --dry-run     # preview
python3 -m mce push data/leads.csv --limit 50               # import to GHL (no calls)
python3 -m mce push data/leads.csv --limit 50 --queue       # import AND start the call workflow
python3 -m mce results                                      # export answered / no-answer
```

Env vars: `GHL_TOKEN`, `GHL_LOCATION_ID`, `SCRAPINGBEE_API_KEY`.
Workflow setup: `docs/ghl-dialer-workflow.md`.

## Line types
Mobile numbers are **never auto-dialed**: they get tags `mce-line-mobile` + `mce-cell-manual`, a call task, and (if the pipeline exists) an opportunity in "Missed Call Prospects" > "Manual Call - Cell". They are still imported and still get the next-day email. Numbers with an unknown line type are held out of the dial queue unless you pass `--allow-unknown`.
