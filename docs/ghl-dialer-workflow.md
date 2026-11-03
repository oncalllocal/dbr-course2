# GHL workflow: after-hours prospecting call

Build this in the **prospecting sub-account** (the API cannot create workflows).

## Tags and fields (already created by the importer / existing in the account)
| Name | Meaning |
|---|---|
| `mce-prospect` | Lead imported by the scraper |
| `mce-dial-queue` | **Adding this tag starts the call workflow** |
| `mce-answered` | A person/system picked up live. Not a prospect. |
| `mce-no-answer` | Nobody picked up. **Viable prospect.** |
| `mce-24-7` | Listing claims 24 hours/emergency service. Call these first. |
| Custom field `audit_outcome` | `answered`, `voicemail`, `ringout`, `failed` |
| Custom fields `audit_call_day` / `audit_call_time` | When the attempt happened |

## Workflow A: "MCE – Dial Test"
**Trigger:** Contact Tag Added = `mce-dial-queue`

1. **Wait until the calling window.** Mon-Thu, 5:30 PM-8:30 PM in the contact's local time zone (use the Wait step's time-window option; if the step lacks it, use an If/Else on current time and loop back with a delay).
2. **Outbound call** with the prerecorded message (see `voice-message-options.md`). Use the same call action you already tested. Requirement: the action must expose a call-status result so you can branch on it.
3. **If/Else on call status:**
   - **Answered** (a live person or answering service picked up): add tag `mce-answered`, set `audit_outcome = answered`, remove tag `mce-dial-queue`. End.
   - **Anything else** (no answer, voicemail, busy, failed): go to step 4.
4. **Attempt 2 (recommended).** Wait until the next evening's window, repeat the call. Two misses on different nights avoids false positives from one bad moment. Skip this step if you want speed over accuracy.
5. **If both attempts missed:**
   - Add tag `mce-no-answer`; remove `mce-dial-queue`.
   - Set `audit_outcome` = `voicemail` or `ringout` (if the call action reports it; otherwise `no-answer`).
   - Set `audit_call_day` = `{{right_now.day_of_week}}`, `audit_call_time` = `{{right_now.time}}`.
   - **Create Task**: assigned to you, due tomorrow 9:00 AM, title `Call {{contact.company_name}}: missed our call last night`, description `{{contact.phone}} / {{contact.website}}`.
   - **Send Internal Notification (SMS) to you**: `Prospect: {{contact.company_name}} {{contact.phone}} did not answer.` Consider a daily digest instead of one SMS per lead once volume grows.
   - **Create/Update Opportunity**: pipeline "Missed Call Prospects", stage "Did not answer".
6. Next-day email: trigger on tag `mce-no-answer`, wait until 9 AM next morning, send email (copy comes in the next deliverable). Only after the sending domain is warmed.

## Compliance guardrails baked in
- Calling window restricted in the workflow (step 1).
- Honor "do not call" requests: add a Workflow B that removes the contact from all queues and adds tag `dnd-call` when a contact is marked DND.
- The message must identify your business and give a callback number.
