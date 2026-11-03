// Logs in to GHL with GHL_DEMO_EMAIL / GHL_DEMO_PASSWORD (env only) and saves the session to <scratch>/ghl_state.json.
// If GHL asks for a one-time code, writes <scratch>/status.txt=NEEDS_OTP and waits up to 10 min for <scratch>/otp.txt.
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path');
const SC = process.argv[2], status = s => { fs.writeFileSync(path.join(SC, 'status.txt'), s); console.log('status:', s); };
const email = process.env.GHL_DEMO_EMAIL, pw = process.env.GHL_DEMO_PASSWORD;
if (!email || !pw) { console.error('GHL_DEMO_EMAIL / GHL_DEMO_PASSWORD not set'); process.exit(2); }
(async () => {
  const proxy = process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined;
  const b = await chromium.launch({ proxy });
  const ctx = await b.newContext({ viewport: { width: 1600, height: 900 } }); const p = await ctx.newPage();
  await p.goto('https://app.gohighlevel.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await p.fill('#email', email); await p.fill('#password', pw);
  await p.click('button[type=submit]');
  const deadline = Date.now() + 90000; let state = 'unknown';
  while (Date.now() < deadline) {
    await p.waitForTimeout(2500);
    const url = p.url(), body = (await p.innerText('body').catch(() => '')).toLowerCase();
    if (/security code|verification code|6-digit|enter the code|one-time/.test(body)) { state = 'otp'; break; }
    if (/incorrect|invalid (email|password|credentials)|wrong password/.test(body) && /login|^https:\/\/app\.gohighlevel\.com\/?$/.test(url)) { state = 'badcreds'; break; }
    if (!/\/(login|reset)|gohighlevel\.com\/?$/.test(url) || /dashboard|location|agency|launchpad/.test(url)) { state = 'in'; break; }
  }
  await p.screenshot({ path: path.join(SC, 'after_login.png') });
  console.log('url after submit:', p.url().replace(/\?.*/, ''), '| state:', state);
  if (state === 'otp') {
    status('NEEDS_OTP'); const f = path.join(SC, 'otp.txt'); const end = Date.now() + 600000;
    while (Date.now() < end && !fs.existsSync(f)) await p.waitForTimeout(2000);
    if (!fs.existsSync(f)) { status('OTP_TIMEOUT'); await b.close(); process.exit(3); }
    const code = fs.readFileSync(f, 'utf8').trim().replace(/\D/g, ''); fs.unlinkSync(f);
    const boxes = await p.$$('input:not([type=hidden])');
    if (boxes.length >= 6) { for (let i = 0; i < 6; i++) await boxes[boxes.length - 6 + i].fill(code[i] || ''); } else { await p.keyboard.type(code, { delay: 120 }); }
    await p.waitForTimeout(1500); const btn = await p.$('button[type=submit], button:has-text("Verify"), button:has-text("Confirm")'); if (btn) await btn.click().catch(() => {});
    await p.waitForTimeout(8000); await p.screenshot({ path: path.join(SC, 'after_otp.png') }); state = /\/login|gohighlevel\.com\/?$/.test(p.url()) ? 'otp_failed' : 'in';
    console.log('url after code:', p.url().replace(/\?.*/, ''), '| state:', state);
  }
  if (state === 'in') { await p.waitForTimeout(6000); await ctx.storageState({ path: path.join(SC, 'ghl_state.json') }); status('LOGGED_IN'); } else status(state.toUpperCase());
  await b.close(); process.exit(state === 'in' ? 0 : 1);
})().catch(e => { console.error('ERR', e.message.slice(0, 300)); process.exit(1); });
