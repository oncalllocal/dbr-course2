# Missed Call Text Back (MCTB): Product and Build Blueprint (DRAFT v1, for approval)

Built the same way as the DBR course (`oncalllocal/dbr-course`): spec-driven GHL snapshot, lesson JSON to narrated MP4, SOP and REF PDFs, a release gate, real screenshots captured from a demo account, and a calculator.

**Offer:** $247 setup + $247/mo (first month $494). No contract, cancel anytime. Usage (texts, calls, AI) billed at cost-plus. Billing via QuickBooks now, GHL SaaS mode later.
**Promise (replaces money-back):** if no missed caller has been captured and texted back after 60 days *with forwarding verified active and the 30 day usage report on file*, we keep working free until the first captured lead. (Owner wording to confirm.)
**Targets:** home service companies, especially 24/7 and emergency trades and owner-in-the-field shops.
**Case study (real, owner-supplied):** $12M/yr company with human 24/7 answering; MCTB as backup converted $83,000 so far this year. Needs the client's written OK and redaction.

---

## System map

| Stage | What happens | Where it lives |
|---|---|---|
| 1. Find | Scrape Google Maps by trade and city, score (24/7, small review count) | `mce/` (built) |
| 2. Test call | After-hours prerecorded call from the prospecting sub-account; answered vs not | GHL workflow, `docs/ghl-dialer-workflow.md` |
| 3. Alert | `mce-no-answer`: GHL task + SMS to owner, opportunity created | GHL workflow |
| 4. Email | Next morning email: "we called, no answer, here is what that costs you" + calculator + demo link | Cold-email sequence (to write) |
| 5. Demo | Pre-trained demo bot per prospect, booking link | Demo build (to design) |
| 6. Close | Owner call, payment (QuickBooks), onboarding form | Sales + onboarding |
| 7. Onboard | Sub-account from the MCTB snapshot, A2P, locked-down user, forwarding | `docs/SNAPSHOT_BUILD_SPEC.md` + SOPs |
| 8. Run | Missed call: text 1 immediately (any hour), text 2 at 10 min, then 8:30-4:30 only; AI qualifies; summary + transcript to the owner | Snapshot workflows |
| 9. Retain | Monthly report, follow-ups, usage billing | Report workflow |

## Deliverable set (mirrors the DBR course)

### A. Sales assets
| ID | Asset | Format |
|---|---|---|
| S-01 | Promo video: sell the hole, not the drill (cost of one missed call, then the fix) | MP4 via pipeline, real screenshots |
| S-02 | Cold email sequence (day-after-call email + 3 follow-ups) | Copy doc, GHL templates |
| S-03 | Prerecorded call message (3 options) | `docs/voice-message-options.md` |
| S-04 | Missed-call calculator (calls missed x close rate x average job) | `calculator/` (adapt DBR calculator) |
| S-05 | Case study one-pager | PDF |
| S-06 | Demo bot (pre-trained on the prospect's public info) + booking link | GHL |
| S-07 | Proof statistics sheet (sources cited, no unsourced numbers) | Doc |

### B. Client course: "How to use your Missed Call Text Back" (usage only)
Different from the DBR course, which taught setup. **We build and configure everything**, so the client course teaches only how to *use* the finished system from a **locked-down GHL user** (Conversations, Contacts, Phone, Dashboard; nothing else). About 11 lessons of 3-5 minutes, about 40 minutes total.

| Module | Lessons |
|---|---|
| 1. How it works | 1.1 What happens when you miss a call (the flow, with a real conversation); 1.2 What we already set up for you, and what you never need to touch |
| 2. Get in | 2.1 Log in, bookmark it, install the mobile app, turn on notifications; 2.2 Your one job on your side: forward your phone after N rings (short, carrier-specific, see SOP-02) |
| 3. Use your account | 3.1 Conversations: read the thread and the AI summary; 3.2 Contacts: find a lead, see their history; 3.3 Phone and call history: call back from your business number; 3.4 Alerts: what you get and when |
| 4. Turn leads into jobs | 4.1 Call back fast: what to say, using the AI's notes; 4.2 Take over from the AI, reply yourself, and handle STOP and opt-outs |
| 5. Help | 5.1 If something looks wrong, and how to ask us for a change (clients cannot edit workflows) |

Client SOPs (PDF): SOP-01 Log in and install the app; SOP-02 Forward your calls; SOP-03 Test your system (place a test call, see the text arrive); SOP-04 Conversations and taking over from the AI; SOP-05 Contacts and call-back scripts; SOP-06 Troubleshooting. REF: Glossary, FAQ, What the AI says and how it is trained on your company.

**Deliberately not in the client course** (we do it, so it moves to internal ops): sub-account creation, snapshot import, A2P and number registration, domains and email authentication, workflow editing, list import and cleaning, launch pacing.

**Screenshots** come from the demo sub-account while logged in as the **locked-down client user**, so clients see exactly the menus they will have.

### C. Internal ops (not client-facing)
- `docs/SNAPSHOT_BUILD_SPEC.md`: the client snapshot (workflows, fields, tags, AI bot prompt, user role permissions).
- `docs/OPS_ONBOARDING.md`: our checklist for each new client: sub-account from the snapshot, AI bot trained on their company, A2P brand and campaign, number purchase, locked-down user and permissions, forwarding verification, test call, go-live.
- `docs/ghl-dialer-workflow.md` and the `mce/` prospecting tool.

## Build conventions (copied from DBR)
- One JSON per lesson in `lessons/`; narration under 120 words per slide; no brackets or URLs in narration.
- Real screenshots only, captured by `tools/ghl/` from a **demo** sub-account (credentials via `GHL_DEMO_EMAIL` and `GHL_DEMO_PASSWORD`, never in the repo).
- Render: `node pipeline/build.js --silent lessons/X.json` for drafts; ElevenLabs for the final.
- A release gate (to be adapted from DBR's `tools/release_gate.py`) must pass before voicing.
- Compliance tone: "not legal advice", opt-out always honored (STOP), no income guarantees.

## Open decisions
1. Brand: reuse OnCallLocal brand (colors #00437A / #F47920, support@oncalllocal.com) or a separate product brand?
2. Who is the voice (ElevenLabs voice id) for training videos vs the promo?
3. Demo sub-account and a **locked-down test user that matches the client role** (`GHL_DEMO_EMAIL`, `GHL_DEMO_PASSWORD`, `GHL_DEMO_LOCATION_ID`).
4. Which user permissions the client role gets (proposed: Conversations, Contacts, Phone, Dashboard; nothing else).
5. Final wording of the guarantee, and the written OK for the $83,000 case study.
