# MCTB on GitHub Actions (cutover guide)

Three workflows replace the Claude scheduled sessions. Each keeps a log of every run and keeps secrets in GitHub's store. Scheduled runs stay OFF until the repository variable `MCTB_ACTIONS_LIVE` is `true`. Manual runs (Run workflow) always work.

| Workflow | File | When | What |
|---|---|---|---|
| MCTB dialer | dialer.yml | Mon-Thu 7:00 PM ET (crons 22:45 and 23:45 UTC, code checks the window) | `mce dial --live --limit 80 --wait-minutes 30` |
| MCTB email 1 | email1.yml | Mon-Fri 9:05 AM ET window (crons 12:50 / 13:50 UTC) | `mce email --live --limit 25` |
| MCTB replies | replies.yml | GHL webhook (instant) + hourly backup | classify replies, build video + DRAFT email, notify owner |

## 1. Repository secrets (Settings > Secrets and variables > Actions > Secrets)
`GHL_TOKEN`, `GHL_LOCATION_ID`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `ELEVENLABS_API_KEY`, `SCRAPINGBEE_API_KEY`

## 2. Dry-run each workflow
Actions tab > pick the workflow > Run workflow with `live` = false (replies: leave contact_id empty). Read the log: window state, queue counts, no errors. The replies run needs no contact id for a scan.

## 3. GHL webhook for instant replies (optional; hourly backup works without it)
1. GitHub > Settings > Developer settings > Fine-grained tokens: repository `oncalllocal/dbr-course2` only, permission Actions = Read and write.
2. In the GHL "MCTB | Reply Handler" workflow add a Webhook action:
   - POST `https://api.github.com/repos/oncalllocal/dbr-course2/actions/workflows/replies.yml/dispatches`
   - Headers: `Authorization: Bearer <PAT>`, `Accept: application/vnd.github+json`
   - Body: `{"ref":"main","inputs":{"contact_id":"{{contact.id}}"}}`

## 4. Cutover (in this order, never both at once)
1. Merge `actions` into `main` (done when you read this).
2. Dry runs pass (step 2).
3. Set repository variable `MCTB_ACTIONS_LIVE` = `true` (Variables tab).
4. Tell Claude to disable the scheduled tasks: dialer `trig_014z5JVJbPFuEjTK9rVCUUVq`, hourly reply check `trig_014MQEFhGdq4X7oWkDinNRTF`, one-time Email 1 `trig_01S7kerLrQAFPfTE3dbiW5FZ` (9:05 AM Thu).

## Safety nets that stay on
Calling-window check, `mce-called-YYYYMMDD` same-day guard, concurrency group (no overlapping dialer runs), `mce-reply-processed` tag (no duplicate drafts).

## Emergency stop
Tag any contact `mce-pause` in GHL: live dialer runs print PAUSED and dial nobody. Or set `MCTB_ACTIONS_LIVE` to `false`.
