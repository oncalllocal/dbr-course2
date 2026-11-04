# Twilio dialer

```
python3 -m mce dial --limit 25                 # dry run against the GHL queue (tag mce-dial-queue)
python3 -m mce dial --live --sms               # dial for real inside the window, text the owner a summary
python3 -m mce dial --from-csv data/x.csv      # dry run against a CSV (never writes to GHL)
```

Env: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` (voice-capable, E.164), optional `OWNER_PHONE` for the SMS digest.

**Flow:** queue (GHL tag `mce-dial-queue`, set by `mce push --queue`; mobile numbers never get it) -> call inside the window (default Mon-Thu 5:30-8:30 PM Eastern) -> Twilio answering-machine detection -> outcome written to GHL.

| Outcome | Meaning | Result |
|---|---|---|
| answered | person or live answering service picked up (or detection unsure) | tag `mce-answered`, removed from queue |
| voicemail | machine picked up | a miss; no message left unless `--leave-voicemail` |
| ringout | no answer, busy, failed | a miss |

Two misses on different evenings -> tag `mce-no-answer`, a GHL task, removed from queue. The first miss tags `mce-attempt-1` and keeps the lead queued for the next evening's run. The next-day email workflow in GHL triggers on `mce-no-answer`.

Guardrails: `--live` required to dial; refuses outside the window; skips contacts with DND, `mce-dnc` or `mce-cell-manual`; pacing between calls (default 8 s).
