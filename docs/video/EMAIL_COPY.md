# Cold email copy: after-hours audit sequence (DRAFT v1)

Send to the best address found: personal-looking (owner) first, then info/contact/office, then any other. Leads with no email stay on the call-only path.
Send the morning after the SECOND miss (9:00 AM recipient time, Tue-Fri). Footer on every email: sender name, OnCall Local, physical address, one-click unsubscribe (CAN-SPAM).

Merge fields: `{{contact.company_name}}`, `{{contact.audit_call_day}}`, `{{contact.audit_call_time}}`, and **`{{contact.mctb_big_job}}`** (to be created: set from the trade at import, e.g. plumbing = "a $12,000 whole-home repipe", HVAC = "a $15,000 system replacement"; other trades need owner-approved figures).

All claims are true or conditional. Do not state that the recipient lost a job. Do not use third-party statistics.

---
## Email 1, version A (first person, "we" as the company)
**Subject options** (test): `No one picked up at {{contact.audit_call_time}}` / `We called {{contact.company_name}} last night` / `Quick question about your after-hours calls`

Hi there,

We called {{contact.company_name}} {{contact.audit_call_day}} night at {{contact.audit_call_time}} as part of an after-hours phone audit we're running for local service companies. Nobody picked up.

I'm not writing to scold you. I'm writing because of what that call could have been.

If that had been a real customer, someone whose home just flooded and who needed {{contact.mctb_big_job}}, they wouldn't have waited for a callback. They would have hung up and called the next company on Google. And you would never have known the call happened.

That's the part that stings: it isn't the one call, it's that the biggest jobs often come in at the worst times, from people who need an answer right now.

There's a simple fix, and it costs far less than a single job. The moment a call goes unanswered, the caller gets a text from your business. An assistant finds out who they are and what they need, and the whole conversation lands on your phone so you can call them back first.

Would you mind if I sent you a short video (under 5 minutes) showing exactly how it works? Just reply "yes" and I'll send it over.

Sam
OnCall Local

## Email 1, version B (third person)
**Subject:** `OnCall Local called {{contact.company_name}} at {{contact.audit_call_time}}`

Hello,

OnCall Local called {{contact.company_name}} {{contact.audit_call_day}} night at {{contact.audit_call_time}} as part of an after-hours phone audit for local service companies. Nobody answered.

Consider what that call could have been. A homeowner with an emergency, ready to book {{contact.mctb_big_job}}. When nobody answers, most people don't leave a message. They call the next company on the list, and the first company to answer gets the job.

A missed-call text-back system fixes this. When a call goes unanswered, the caller receives an instant text from your business, an assistant collects their name and the problem, and the full conversation is sent to you so you can call back first.

May we send you a short video (under 5 minutes) that shows exactly how it works? Reply "yes" and we will.

Sam
OnCall Local

---
## Email 2 (sent after a reply of "yes")
**Subject:** `Your video: what a missed call really costs`

Thanks for saying yes. Here's the video (under 5 minutes):

{{video_link}}

It covers what an unanswered after-hours call can cost, how the text-back works, and founder pricing: $497 for the first month, then $247 a month, no contract.

If it makes sense, just reply to this email and I'll get you set up. If you have questions, reply with those instead.

Sam
OnCall Local

## Email 3 (bump, 3 days after Email 1 with no reply)
**Subject:** `Re: No one picked up at {{contact.audit_call_time}}`

Hi again, just checking that my note about our after-hours call reached you. If it's not a priority, no problem. If it is, reply "yes" and I'll send the 5-minute video.

Sam
OnCall Local
