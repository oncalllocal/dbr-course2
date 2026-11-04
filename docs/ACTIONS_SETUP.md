# Moving the dialer to a GitHub Action (planned for 2026-11-05)

Why: the Claude scheduled session must clone the repo and can fail silently. An Action keeps a log of every run and keeps secrets in GitHub's store.

## Add these repository secrets (Settings > Secrets and variables > Actions)
`GHL_TOKEN`, `GHL_LOCATION_ID`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`

## Switch-over checklist (do in this order, never both at once)
1. Confirm the 2026-11-04 scheduled-session run worked (counts, tags, notes).
2. Merge `lead-pool` into `main` (the workflow file must be on the default branch).
3. Actions tab > "MCTB dialer" > Run workflow with `live` = false. Read the log: window state and queue count should be right.
4. Uncomment the `schedule:` block in `.github/workflows/dialer.yml`.
5. Disable the Claude scheduled task `MCTB after-hours dialer (Mon-Thu 7 PM ET)` (trigger `trig_014z5JVJbPFuEjTK9rVCUUVq`).
6. Safety nets that stay on: the calling-window check, the `mce-called-YYYYMMDD` same-day guard, and the `mce-pause` tag.

## Emergency stop
Tag any contact `mce-pause` in GHL. A live dialer run prints PAUSED and dials nobody until the tag is removed.
(Make one contact named "MCTB SYSTEM CONTROL" for this and leave it untagged normally.)
