// Renders a clearly-labelled EXAMPLE text conversation as a 1600x900 slide image (lessons/shots/9.1-example-chat.png).
const { chromium } = require('playwright'); const path = require('path');
const msgs = [
  ['in',  'Hi! Sorry we missed your call. This is the virtual assistant for Example Plumbing. What is going on, and how can we help?'],
  ['out', 'water heater just burst, water all over the garage'],
  ['in',  'That sounds stressful. Is the water still running? If you can, shut off the water at the main valve. What is the best address for the job?'],
  ['out', 'water is off. 412 Maple Ct'],
  ['in',  'Thank you. I have sent this to the owner and they will call you back shortly.'],
];
const html = `<html><body style="margin:0;width:1600px;height:900px;background:#eef3f8;font-family:Inter,Segoe UI,Arial,sans-serif;display:flex;align-items:center;justify-content:center">
<div style="width:760px;background:#fff;border-radius:44px;box-shadow:0 20px 60px rgba(0,67,122,.25);padding:34px 30px 30px;position:relative">
 <div style="text-align:center;font-weight:700;color:#00437A;font-size:26px;padding-bottom:14px;border-bottom:1px solid #e3eaf1">Text Messages</div>
 <div style="display:flex;flex-direction:column;gap:16px;padding-top:22px">
 ${msgs.map(([d, t]) => `<div style="align-self:${d === 'out' ? 'flex-end' : 'flex-start'};max-width:78%;padding:16px 22px;border-radius:26px;font-size:25px;line-height:1.35;${d === 'out' ? 'background:#F47920;color:#fff' : 'background:#e9eef4;color:#13293d'}">${t}</div>`).join('')}
 </div>
 <div style="position:absolute;top:-22px;left:50%;transform:translateX(-50%);background:#00437A;color:#fff;font-weight:700;font-size:24px;padding:8px 26px;border-radius:30px;letter-spacing:.06em">EXAMPLE CONVERSATION</div>
</div></body></html>`;
(async () => { const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1600, height: 900 } }); await p.setContent(html);
  await p.screenshot({ path: path.join(__dirname, '../lessons/shots/9.1-example-chat.png') }); await b.close(); console.log('ok'); })();
