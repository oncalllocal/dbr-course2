# GHL screenshot capture tooling

Drives the **Demo DBR Account** with headless Chromium to capture real screens for the lessons.

- Credentials come only from the env vars `GHL_DEMO_EMAIL` / `GHL_DEMO_PASSWORD`. The saved session (`ghl_state.json`) is written to the session scratchpad, never into the repo.
- `login.js <scratch>`: logs in; if GHL asks for a one-time code it writes `status.txt=NEEDS_OTP` and waits for `otp.txt`.
- `lib.js`: `open()`, `go()` (waits for "Loading new sub account data", retries bounces), `settled()`.
- `nav_map.json`: real URL paths in the account, verified by clicking the app's own menus. Do not guess paths; several differ from older docs (e.g. `settings/fields`, `settings/pipeline`, `settings/smtp_service`).
- The location id is auto-detected from the account the login lands in (override with `GHL_LOCATION_ID`). Copy `accounts.example.json` to `accounts.json` (git-ignored) for a default, or always set `GHL_LOCATION_ID`. Scripts that change the live account (publish, delete, import, snapshot, submit) refuse to run without `--yes`; `load_content.js` is a dry run unless you pass `--save`.
- `click_nav.js`, `probe_deeplinks.js`, `survey2.js`, `list_accounts.js`, `explore_*.js`: read-only exploration helpers.

Guardrails: never purchase numbers, submit A2P/brand registrations, change domains, connect third-party accounts, or send messages from the demo account. Only additive, clearly named demo data.
