// Shared helpers for driving the GHL demo account. Credentials/session never live in the repo.
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path');
const fromFile = () => { try { return require('./accounts.json').capture || null; } catch (e) { return null; } }; // accounts.json is local-only (see accounts.example.json)
let LOC = process.env.GHL_LOCATION_ID || fromFile() || null; // auto-detected from the landing URL when not set
const base = () => `https://app.gohighlevel.com/v2/location/${LOC}`;
async function open(SC, { width = 1600, height = 900 } = {}) {
  const browser = await chromium.launch({ proxy: process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined });
  const ctx = await browser.newContext({ viewport: { width, height }, storageState: path.join(SC, 'ghl_state.json') });
  const page = await ctx.newPage(); return { browser, ctx, page };
}
const bodyText = async p => (await p.innerText('body').catch(() => '')).replace(/\s+/g, ' ');
/** Wait for the SPA to finish "Loading new sub account data" and for the network to settle. */
async function settled(p, ms = 60000) {
  const end = Date.now() + ms;
  while (Date.now() < end) { const t = await bodyText(p); if (!/loading new sub ?account data/i.test(t) && t.length > 80) break; await p.waitForTimeout(1000); }
  await p.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {}); await p.waitForTimeout(2500);
}
/** Go to a location-relative path; if GHL bounces us elsewhere (it does while the account loads), retry. */
async function go(p, rel, { tries = 3, expect } = {}) {
  if (!LOC) { await p.goto('https://app.gohighlevel.com/', { waitUntil: 'domcontentloaded', timeout: 60000 }); await settled(p, 45000); LOC = (p.url().match(/location\/([A-Za-z0-9]+)/) || [])[1]; if (!LOC) throw new Error('could not detect location id from ' + p.url()); console.log('using location', LOC); }
  for (let i = 0; i < tries; i++) {
    await p.goto(`${base()}/${rel}`, { waitUntil: 'domcontentloaded', timeout: 60000 }); await settled(p);
    if (p.url().includes(expect || rel.split('?')[0])) return true;
    await p.waitForTimeout(3000);
  }
  return false;
}
/** Refuse to run an outward or destructive action unless the operator typed --yes (or set GHL_ALLOW=1). Prints what would happen. */
function requireYes(what) {
  if (process.argv.includes('--yes') || process.env.GHL_ALLOW === '1') return;
  console.error(`REFUSING: ${what}\nThis script changes the live account. Re-run with --yes if that is what you want.`); process.exit(2);
}
const locId = () => LOC || process.env.GHL_LOCATION_ID || fromFile();
module.exports = { open, go, settled, bodyText, base, requireYes, locId, getLoc: () => LOC };
